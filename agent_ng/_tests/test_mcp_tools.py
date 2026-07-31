"""Unit tests for external MCP registry loading (no live MCP servers)."""

from pathlib import Path

import pytest
import yaml

from agent_ng.mcp_tools import (
    DEFAULT_MCP_SERVERS_FILE,
    is_mcp_enabled,
    load_mcp_registry,
    merge_tools,
    reset_mcp_tools_cache,
)


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMW_MCP_ENABLED", raising=False)
    monkeypatch.delenv("CMW_MCP_ALLOWED_SERVERS", raising=False)
    monkeypatch.delenv("CMW_MCP_ALLOWED_HOSTS", raising=False)
    reset_mcp_tools_cache()


def test_mcp_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMW_MCP_ENABLED", raising=False)
    assert is_mcp_enabled() is False


def test_default_registry_path_is_tracked_config() -> None:
    assert DEFAULT_MCP_SERVERS_FILE.name == "mcp_servers.yaml"
    assert DEFAULT_MCP_SERVERS_FILE.parent.name == "config"
    assert DEFAULT_MCP_SERVERS_FILE.resolve() == DEFAULT_MCP_SERVERS_FILE


def test_tracked_registry_file_exists() -> None:
    assert DEFAULT_MCP_SERVERS_FILE.is_file()


def test_tracked_registry_lists_ennoia_producer() -> None:
    connections = load_mcp_registry(DEFAULT_MCP_SERVERS_FILE)
    assert "comindware_kb" in connections
    url = connections["comindware_kb"]["url"]
    assert "ennoia.slickjump.org" in url
    assert "get_knowledge_base_articles" in url
    assert connections["comindware_kb"]["transport"] == "streamable_http"


def test_allowed_servers_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = tmp_path / "mcp.yaml"
    registry.write_text(
        yaml.dump(
            {
                "alpha": {"transport": "http", "url": "https://a.example/gradio_api/mcp/"},
                "beta": {"transport": "http", "url": "https://b.example/gradio_api/mcp/"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CMW_MCP_ALLOWED_SERVERS", "beta")
    connections = load_mcp_registry(registry)
    assert set(connections) == {"beta"}


def test_invalid_transport_raises(tmp_path: Path) -> None:
    registry = tmp_path / "mcp.yaml"
    registry.write_text(
        yaml.dump({"bad": {"transport": "ftp", "url": "https://x.example/mcp"}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Phase 1 supports HTTP MCP only"):
        load_mcp_registry(registry)


def test_merge_tools_skips_name_collisions() -> None:
    class _Tool:
        def __init__(self, name: str) -> None:
            self.name = name

    native = [_Tool("dup"), _Tool("only_native")]
    mcp = [_Tool("dup"), _Tool("mcp_only")]
    merged = merge_tools(native, mcp)
    assert [t.name for t in merged] == ["dup", "only_native", "mcp_only"]


def test_env_var_substitution_in_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = tmp_path / "mcp.yaml"
    registry.write_text(
        yaml.dump(
            {
                "kb": {
                    "transport": "http",
                    "url": "https://example-host/gradio_api/mcp/",
                    "headers": {
                        "Authorization": "Bearer ${REMOTE_MCP_BEARER_TOKEN}",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("REMOTE_MCP_BEARER_TOKEN", "test-token-abc")
    connections = load_mcp_registry(registry)
    assert connections["kb"]["headers"]["Authorization"] == "Bearer test-token-abc"


def test_missing_env_var_expands_to_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = tmp_path / "mcp.yaml"
    registry.write_text(
        yaml.dump(
            {
                "kb": {
                    "transport": "http",
                    "url": "https://example-host/gradio_api/mcp/",
                    "headers": {"Authorization": "Bearer ${REMOTE_MCP_BEARER_TOKEN}"},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("REMOTE_MCP_BEARER_TOKEN", raising=False)
    connections = load_mcp_registry(registry)
    assert connections["kb"]["headers"]["Authorization"] == "Bearer "


def test_tracked_registry_never_requires_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REMOTE_MCP_BEARER_TOKEN", raising=False)
    connections = load_mcp_registry(DEFAULT_MCP_SERVERS_FILE)
    assert "headers" not in connections["comindware_kb"]


def test_servers_wrapper_key(tmp_path: Path) -> None:
    registry = tmp_path / "mcp.yaml"
    registry.write_text(
        yaml.dump(
            {
                "servers": {
                    "wrapped": {
                        "transport": "streamable_http",
                        "url": "https://example-host/gradio_api/mcp/",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    connections = load_mcp_registry(registry)
    assert "wrapped" in connections
    assert connections["wrapped"]["transport"] == "streamable_http"


@pytest.mark.asyncio
async def test_fetch_mcp_tools_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from agent_ng import mcp_tools
    from agent_ng.mcp_tools import load_mcp_registry as _load_mcp_registry_impl

    registry = tmp_path / "s.yaml"
    monkeypatch.setenv("CMW_MCP_ENABLED", "true")
    registry.write_text(
        yaml.dump(
            {
                "kb": {
                    "transport": "http",
                    "url": "https://example-host/gradio_api/mcp/",
                }
            }
        ),
        encoding="utf-8",
    )

    mock_tool = MagicMock()
    mock_tool.name = "get_knowledge_base_articles"
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=[mock_tool])

    def _load_registry(_path=None):
        return _load_mcp_registry_impl(registry)

    with (
        patch.object(mcp_tools, "load_mcp_registry", side_effect=_load_registry),
        patch(
            "langchain_mcp_adapters.client.MultiServerMCPClient",
            return_value=mock_client,
        ),
    ):
        tools = await mcp_tools.fetch_mcp_tools_async()

    assert len(tools) == 1
    assert tools[0].name == "get_knowledge_base_articles"


def test_build_multi_client_kwargs_drops_unsupported_kwargs() -> None:
    """``MultiServerMCPClient.__init__`` shape varies across
    ``langchain-mcp-adapters`` versions (0.1.x accepts only ``connections``;
    0.2.x adds ``tool_name_prefix`` / ``tool_interceptors``). The kwargs builder
    must drop params that the installed version does not support, so callers
    can safely pass the resulting dict to the real constructor.
    """

    class _StubClient:
        def __init__(self, connections):
            self.connections = connections

    connections = {"kb": {"transport": "http", "url": "https://x.example/mcp"}}
    from agent_ng import mcp_tools

    # 0.1.x-shaped signature: only ``connections`` is supported.
    kwargs = mcp_tools._build_multi_client_kwargs(
        connections=connections,
        prefix_enabled=True,
        interceptor=_StubClient,  # any sentinel — must be dropped
        signature_params=("connections",),
    )
    assert kwargs == {"connections": connections}

    # 0.2.x-shaped signature: all extra kwargs are forwarded.
    kwargs = mcp_tools._build_multi_client_kwargs(
        connections=connections,
        prefix_enabled=True,
        interceptor=_StubClient,
        signature_params=("connections", "tool_name_prefix", "tool_interceptors"),
    )
    assert kwargs["connections"] is connections
    assert kwargs["tool_name_prefix"] is True
    assert kwargs["tool_interceptors"] == [_StubClient]


@pytest.mark.asyncio
async def test_fetch_mcp_tools_does_not_pass_unsupported_kwargs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end guard: ``fetch_mcp_tools_async`` must not forward
    ``tool_name_prefix`` / ``tool_interceptors`` to a ``MultiServerMCPClient``
    that doesn't declare them. We assert this by checking the call args
    against the real installed signature.
    """
    import inspect
    from unittest.mock import AsyncMock, MagicMock, patch

    from agent_ng import mcp_tools
    from agent_ng.mcp_tools import load_mcp_registry as _load_mcp_registry_impl

    registry = tmp_path / "s.yaml"
    monkeypatch.setenv("CMW_MCP_ENABLED", "true")
    registry.write_text(
        yaml.dump(
            {
                "kb": {
                    "transport": "http",
                    "url": "https://example-host/gradio_api/mcp/",
                }
            }
        ),
        encoding="utf-8",
    )

    mock_tool = MagicMock()
    mock_tool.name = "get_knowledge_base_articles"
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=[mock_tool])

    def _load_registry(_path=None):
        return _load_mcp_registry_impl(registry)

    with (
        patch.object(mcp_tools, "load_mcp_registry", side_effect=_load_registry),
        patch(
            "langchain_mcp_adapters.client.MultiServerMCPClient",
            return_value=mock_client,
        ) as ctor_mock,
    ):
        tools = await mcp_tools.fetch_mcp_tools_async()

    ctor_mock.assert_called_once()
    forwarded = ctor_mock.call_args.kwargs
    # Cross-check: whatever we forwarded must also be accepted by the real
    # installed ``MultiServerMCPClient.__init__`` signature. If this assertion
    # ever fires after an upstream bump, ``_build_multi_client_kwargs``
    # needs to be revisited.
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        pytest.skip("langchain-mcp-adapters not installed")
    real_params = inspect.signature(MultiServerMCPClient.__init__).parameters
    for kwarg in forwarded:
        assert kwarg in real_params, (
            f"fetch_mcp_tools_async forwarded {kwarg!r}, but the installed "
            f"MultiServerMCPClient.__init__ does not accept it. Available: "
            f"{sorted(real_params)}"
        )

    assert len(tools) == 1
    assert tools[0].name == "get_knowledge_base_articles"
