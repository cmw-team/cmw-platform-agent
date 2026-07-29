"""Model tab exposes only the shared model-selection controls."""

import inspect

import gradio as gr

from agent_ng.tabs.config_tab import ConfigTab
from agent_ng.tabs.sidebar import Sidebar


def test_config_tab_source_has_only_model_selection_ui():
    source = inspect.getsource(ConfigTab)

    assert "mount_llm_selection_ui" in source
    assert "config_status_display" in source
    for removed in (
        "BrowserState",
        "platform_url",
        "username",
        "password",
        "llm_provider_api_keys",
        "save_btn",
        "load_btn",
        "clear_storage_btn",
        "_save_to_state",
        "_load_from_state",
        "_clear_browser_storage",
    ):
        assert removed not in source


def test_config_tab_builds_model_controls_only():
    sidebar = Sidebar(event_handlers={}, language="en")
    tab = ConfigTab(event_handlers={}, language="en")
    tab.set_sidebar_instance(sidebar)

    with gr.Blocks():
        tab._create_config_interface()

    assert set(tab.components) == {"config_status_display"}
    assert set(sidebar.components) == {
        "provider_model_selector",
        "use_fallback_model",
        "fallback_model_selector",
    }


def test_config_tab_connect_events_is_noop():
    tab = ConfigTab(event_handlers={}, language="en")
    assert tab._connect_events() is None


