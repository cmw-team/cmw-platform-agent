"""Behavior tests for the ``extract_presentation_slides`` LangChain tool.

These tests cover the tool contract defined in
``.scratch/extract_presentation_slides-contract.md``: source resolution, error
codes, envelope shape, JSON serializability, and isolation between sources.

Resolver-only behavior is exercised via a ``FakeAgent`` and a monkeypatched
``parse_presentation``; integration with the parser itself is covered by
``test_presentation_parser.py``. A separate smoke test consumes the real default
presentations when they are present on disk.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any
import zipfile

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)

DEFAULT_PRODUCT_DECK = "Comindware Platform 6.pptx"
DEFAULT_CASE_LIBRARY = "Comindware Кейсы_1.7.pptx"
PRODUCT_DECK_ALIAS = "default-product-deck"
CASE_LIBRARY_ALIAS = "default-case-library"


class FakeAgent:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def get_file_path(self, original_filename: str) -> str | None:
        return self.files.get(original_filename)


def _presentation_tools_module():
    return importlib.import_module("tools.presentation_tools")


def _tool_module():
    return importlib.import_module(
        "tools.presentation_tools.tool_extract_presentation_slides"
    )


def _shape(
    text_paragraphs: tuple[tuple[str, ...], ...],
    *,
    placeholder: str | None = None,
    shape_id: int = 2,
) -> str:
    placeholder_xml = f'<p:ph type="{placeholder}"/>' if placeholder else ""
    paragraphs = "".join(
        "<a:p>"
        + "".join(f"<a:r><a:t>{run}</a:t></a:r>" for run in runs)
        + "</a:p>"
        for runs in text_paragraphs
    )
    return dedent(
        f"""
        <p:sp>
          <p:nvSpPr>
            <p:cNvPr id="{shape_id}" name="Shape {shape_id}"/>
            <p:cNvSpPr/>
            <p:nvPr>{placeholder_xml}</p:nvPr>
          </p:nvSpPr>
          <p:spPr/>
          <p:txBody>
            <a:bodyPr/>
            <a:lstStyle/>
            {paragraphs}
          </p:txBody>
        </p:sp>
        """
    ).strip()


def _slide_xml(*elements: str) -> str:
    content = "\n".join(elements)
    return dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:sld xmlns:p="{P_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}">
          <p:cSld>
            <p:spTree>
              <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
              </p:nvGrpSpPr>
              <p:grpSpPr/>
              {content}
            </p:spTree>
          </p:cSld>
        </p:sld>
        """
    ).strip()


def _write_minimal_pptx(path: Path, *, title: str) -> Path:
    slide = _slide_xml(_shape(((title,),), placeholder="title"))
    presentation = dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:presentation xmlns:p="{P_NS}" xmlns:r="{R_NS}">
          <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
        </p:presentation>
        """
    ).strip()
    relationships = (
        f'<Relationships xmlns="{PKG_REL_NS}">'
        f'<Relationship Id="rId1" Type="{SLIDE_REL}" Target="slides/slide1.xml"/>'
        f"</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr("ppt/_rels/presentation.xml.rels", relationships)
        archive.writestr("ppt/slides/slide1.xml", slide)
    return path


def _seed_default_presentations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    """Point ``DEFAULT_PRESENTATIONS_DIR`` at *tmp_path* and write fixtures."""
    tool_module = _tool_module()
    monkeypatch.setattr(
        tool_module, "DEFAULT_PRESENTATIONS_DIR", tmp_path
    )
    product = _write_minimal_pptx(
        tmp_path / DEFAULT_PRODUCT_DECK, title="Product deck slide"
    )
    case = _write_minimal_pptx(
        tmp_path / DEFAULT_CASE_LIBRARY, title="Case library slide"
    )
    return product, case


def _stub_parser(
    monkeypatch: pytest.MonkeyPatch,
    *,
    return_value: dict[str, Any] | None = None,
    side_effect: BaseException | None = None,
) -> Any:
    """Replace ``parse_presentation`` with a stub that records calls."""
    tool_module = _tool_module()
    calls: list[Path] = []

    def _stub(file_path: str | Path) -> dict[str, Any]:
        calls.append(Path(file_path))
        if side_effect is not None:
            raise side_effect
        if return_value is not None:
            return return_value
        return {
            "slide_count": 1,
            "capabilities": {
                "text_extraction_complete": True,
                "visual_content_analyzed": False,
            },
            "slides": [],
        }

    monkeypatch.setattr(
        tool_module,
        "parse_presentation",
        _stub,
    )
    return calls


def _fake_parser_payload() -> dict[str, Any]:
    return {
        "slide_count": 2,
        "capabilities": {
            "text_extraction_complete": True,
            "visual_content_analyzed": False,
        },
        "slides": [
            {
                "number": 1,
                "title": "First",
                "title_source": "placeholder",
                "text": "First body",
                "text_length": 10,
                "notes": "",
                "objects": {"pictures": 0, "tables": 0, "charts": 0},
                "warnings": [],
            },
            {
                "number": 2,
                "title": "Second",
                "title_source": "first_text",
                "text": "Second body",
                "text_length": 11,
                "notes": "Speaker note",
                "objects": {"pictures": 0, "tables": 0, "charts": 0},
                "warnings": [],
            },
        ],
    }


def test_tool_call_schema_exposes_only_source_for_model() -> None:
    tool_module = _tool_module()
    raw_tool = tool_module.extract_presentation_slides
    call_schema = raw_tool.tool_call_schema
    properties = call_schema.model_json_schema().get("properties", {})

    assert "source" in properties
    assert "agent" not in properties
    assert "args" not in properties

    assert "source" in raw_tool.args
    assert "agent" in raw_tool.args


def test_default_product_deck_resolves_to_product_presentation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product, _case = _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"] == {
        "requested": PRODUCT_DECK_ALIAS,
        "resolved_name": DEFAULT_PRODUCT_DECK,
        "source_type": "default",
    }
    assert result["error"] is None
    assert calls == [product.resolve()]


def test_default_case_library_resolves_to_case_library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _product, case = _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=CASE_LIBRARY_ALIAS, agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"] == {
        "requested": CASE_LIBRARY_ALIAS,
        "resolved_name": DEFAULT_CASE_LIBRARY,
        "source_type": "default",
    }
    assert calls == [case.resolve()]


def test_uploaded_pptx_is_resolved_via_agent_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_minimal_pptx(
        tmp_path / "client.pptx", title="Client title"
    )
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({"client.pptx": str(upload)})
    result = _tool_module().extract_presentation_slides.func(
        source="client.pptx", agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"] == {
        "requested": "client.pptx",
        "resolved_name": "client.pptx",
        "source_type": "uploaded",
    }
    assert calls == [upload.resolve()]


def test_uploaded_pptx_returns_original_name_when_cache_name_differs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    cached_upload = _write_minimal_pptx(
        tmp_path / "session-42_client-deck_abc123.pptx",
        title="Client title",
    )
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({"client-deck.pptx": str(cached_upload)})
    result = _tool_module().extract_presentation_slides.func(
        source="client-deck.pptx", agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"]["resolved_name"] == "client-deck.pptx"
    assert calls == [cached_upload.resolve()]


@pytest.mark.parametrize(
    "bad_source",
    [
        "",
        "   ",
        "C:\\Users\\yboi\\Desktop\\secret.pptx",
        "C:/Users/yboi/Desktop/secret.pptx",
        "/etc/passwd",
        "..\\secret.pptx",
        "folder\\secret.pptx",
        "folder/secret.pptx",
        "./secret.pptx",
    ],
)
def test_invalid_source_returns_invalid_source(
    bad_source: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=bad_source, agent=agent
    )

    assert result == {
        "success": False,
        "data": None,
        "error": {"code": "invalid_source", "message": result["error"]["message"]},
    }
    assert calls == []


def test_unknown_default_alias_returns_unknown_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source="default-old-deck", agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "unknown_source"
    assert calls == []


@pytest.mark.parametrize("bad_prefix", ["default-", "DEFAULT-", "Default-"])
def test_bare_default_prefix_returns_invalid_source(
    bad_prefix: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=bad_prefix, agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "invalid_source"
    assert calls == []


@pytest.mark.parametrize(
    ("alias_variant", "expected_filename"),
    [
        ("default-product-deck", DEFAULT_PRODUCT_DECK),
        ("DEFAULT-PRODUCT-DECK", DEFAULT_PRODUCT_DECK),
        ("Default-Product-Deck", DEFAULT_PRODUCT_DECK),
        ("default-CASE-library", DEFAULT_CASE_LIBRARY),
    ],
)
def test_default_alias_lookup_is_case_insensitive(
    alias_variant: str,
    expected_filename: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=alias_variant, agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"]["requested"] == alias_variant.lower()
    assert result["data"]["source"]["source_type"] == "default"
    assert calls == [(_default_presentation_path(monkeypatch, expected_filename)).resolve()]


def _default_presentation_path(
    monkeypatch: pytest.MonkeyPatch, filename: str
) -> Path:
    """Return the path the seeded presentations directory points at for *filename*."""
    from tools.presentation_tools import tool_extract_presentation_slides as mod

    return mod.DEFAULT_PRESENTATIONS_DIR / filename


def test_unsupported_format_short_circuits_before_session_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({"brief.docx": str(tmp_path / "brief.docx")})
    result = _tool_module().extract_presentation_slides.func(
        source="brief.docx", agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "unsupported_format"
    assert calls == []


def test_unregistered_upload_returns_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source="missing.pptx", agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "file_not_found"
    assert calls == []


def test_missing_default_file_returns_default_source_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _tool_module(), "DEFAULT_PRESENTATIONS_DIR", tmp_path
    )
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "default_source_missing"
    assert calls == []
    assert calls == []


def test_corrupted_presentation_returns_corrupted_presentation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _product, _case = _seed_default_presentations(tmp_path, monkeypatch)
    tool_module = _tool_module()

    def _raise(path: str | Path) -> dict[str, Any]:
        raise tool_module.CorruptedPresentationError("bad zip")

    monkeypatch.setattr(tool_module, "parse_presentation", _raise)

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "corrupted_presentation"


def test_unexpected_parser_exception_returns_extraction_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _product, _case = _seed_default_presentations(tmp_path, monkeypatch)
    tool_module = _tool_module()

    def _raise(path: str | Path) -> dict[str, Any]:
        msg = "boom with secret password=hunter2"
        raise RuntimeError(msg)

    monkeypatch.setattr(tool_module, "parse_presentation", _raise)

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "extraction_failed"
    assert "hunter2" not in result["error"]["message"]
    assert str(tmp_path) not in result["error"]["message"]
    assert "RuntimeError" not in result["error"]["message"]


def test_successful_response_preserves_parser_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _product, _case = _seed_default_presentations(tmp_path, monkeypatch)
    _stub_parser(monkeypatch, return_value=_fake_parser_payload())

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    data = result["data"]
    assert data["slide_count"] == 2
    assert data["capabilities"] == {
        "text_extraction_complete": True,
        "visual_content_analyzed": False,
    }
    assert data["slides"] == _fake_parser_payload()["slides"]


def test_every_response_is_json_serializable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    _stub_parser(monkeypatch, return_value=_fake_parser_payload())

    agent = FakeAgent({})
    tool_module = _tool_module()

    cases = [
        ("",),
        ("   ",),
        ("C:\\absolute\\path.pptx",),
        ("/absolute/path.pptx",),
        ("default-old-deck",),
        ("brief.docx",),
        ("missing.pptx",),
        (PRODUCT_DECK_ALIAS,),
        (CASE_LIBRARY_ALIAS,),
    ]
    for (source,) in cases:
        payload = tool_module.extract_presentation_slides.func(
            source=source, agent=agent
        )
        json.dumps(payload, ensure_ascii=False)


def test_error_messages_never_leak_paths_or_traces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaked = _write_minimal_pptx(
        tmp_path / "leak_target.pptx", title="leak"
    )
    tool_module = _tool_module()

    def _raise(path: str | Path) -> dict[str, Any]:
        message = "secret failure at " + str(path)
        raise RuntimeError(message)

    monkeypatch.setattr(tool_module, "parse_presentation", _raise)

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    message = result["error"]["message"]
    assert "Traceback" not in message
    assert "RuntimeError" not in message
    assert str(leaked) not in message
    assert "secret" not in message


def test_error_in_one_source_does_not_consult_another(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _product, _case = _seed_default_presentations(tmp_path, monkeypatch)
    tool_module = _tool_module()
    consulted: list[Path] = []

    def _record(path: str | Path) -> dict[str, Any]:
        consulted.append(Path(path))
        raise tool_module.CorruptedPresentationError("bad")

    monkeypatch.setattr(tool_module, "parse_presentation", _record)

    agent = FakeAgent({"alias.pptx": str(_product)})
    result = tool_module.extract_presentation_slides.func(
        source="alias.pptx", agent=agent
    )

    assert result["success"] is False
    assert result["error"]["code"] == "corrupted_presentation"
    assert len(consulted) == 1
    assert consulted[0] == _product.resolve()


def test_package_exports_new_symbols() -> None:
    package = _presentation_tools_module()
    for symbol in (
        "CorruptedPresentationError",
        "ExtractPresentationSlidesSchema",
        "extract_presentation_slides",
        "parse_presentation",
    ):
        assert hasattr(package, symbol), symbol


def _real_default_presentations() -> tuple[Path, Path] | None:
    parser_module = importlib.import_module(
        "tools.presentation_tools.tool_extract_presentation_slides"
    )
    product = parser_module.DEFAULT_PRESENTATIONS_DIR / DEFAULT_PRODUCT_DECK
    case = parser_module.DEFAULT_PRESENTATIONS_DIR / DEFAULT_CASE_LIBRARY
    if product.is_file() and case.is_file():
        return product, case
    return None


@pytest.mark.skipif(
    _real_default_presentations() is None,
    reason="Default presentations are not checked into resources/presentations/",
)
def test_smoke_default_product_deck() -> None:
    paths = _real_default_presentations()
    assert paths is not None

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=PRODUCT_DECK_ALIAS, agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"]["source_type"] == "default"
    assert result["data"]["source"]["resolved_name"] == DEFAULT_PRODUCT_DECK
    assert result["data"]["capabilities"]["visual_content_analyzed"] is False
    assert result["data"]["slide_count"] == len(result["data"]["slides"])
    assert result["data"]["slide_count"] > 0


@pytest.mark.skipif(
    _real_default_presentations() is None,
    reason="Default presentations are not checked into resources/presentations/",
)
def test_smoke_default_case_library() -> None:
    paths = _real_default_presentations()
    assert paths is not None

    agent = FakeAgent({})
    result = _tool_module().extract_presentation_slides.func(
        source=CASE_LIBRARY_ALIAS, agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"]["resolved_name"] == DEFAULT_CASE_LIBRARY
    assert result["data"]["slide_count"] == len(result["data"]["slides"])
    assert result["data"]["slide_count"] > 0


def test_envelope_shape_includes_success_data_error_keys() -> None:
    from langchain_core.tools import render_text_description

    tool_module = _tool_module()
    payload = tool_module.extract_presentation_slides.func(
        source="missing.pptx", agent=FakeAgent({})
    )

    assert set(payload.keys()) == {"success", "data", "error"}
    assert payload["success"] is False
    assert payload["data"] is None
    assert set(payload["error"].keys()) == {"code", "message"}

    description = render_text_description([tool_module.extract_presentation_slides])
    assert "extract_presentation_slides" in description


def test_resolver_strips_whitespace_and_routes_to_uploaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_default_presentations(tmp_path, monkeypatch)
    upload = _write_minimal_pptx(
        tmp_path / "client.pptx", title="Client"
    )
    calls = _stub_parser(
        monkeypatch, return_value=_fake_parser_payload()
    )

    agent = FakeAgent({"client.pptx": str(upload)})
    result = _tool_module().extract_presentation_slides.func(
        source="  client.pptx  ", agent=agent
    )

    assert result["success"] is True
    assert result["data"]["source"]["source_type"] == "uploaded"
    assert calls == [upload.resolve()]
