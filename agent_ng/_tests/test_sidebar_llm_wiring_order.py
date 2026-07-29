"""LLM controls: wire events after stats_display is registered (UIManager merge)."""

from unittest.mock import MagicMock, patch

import gradio as gr

from agent_ng.tabs.sidebar import Sidebar as SidebarPanel


def test_mount_llm_selection_ui_does_not_set_events_connected():
    """Wiring is deferred until ``ensure_llm_events_wired`` (after UIManager merge)."""
    panel = SidebarPanel(event_handlers={}, language="en")
    panel._llm_events_connected = False
    with gr.Blocks(), gr.Column():
        panel.mount_llm_selection_ui()
    assert panel._llm_events_connected is False


def test_apply_llm_selection_update_stats_reads_display_not_combined_toast():
    """Stats after model change must reflect session, not success toast text."""
    panel = SidebarPanel(event_handlers={}, language="en")
    panel.main_app = MagicMock()
    stats_tab = MagicMock()
    stats_tab.format_stats_display.return_value = "__stats_from_tab__"
    panel.main_app.tab_instances = {"stats": stats_tab}

    with patch.object(
        SidebarPanel,
        "_apply_llm_selection_combined",
        return_value="toast would be wrong here",
    ):
        out = panel._apply_llm_selection_update_stats_only("provider_a / model_x", None)

    assert out == "__stats_from_tab__"
    stats_tab.format_stats_display.assert_called_once()


def test_model_selection_has_no_token_budget_variant():
    panel = SidebarPanel(event_handlers={}, language="en")

    assert not hasattr(panel, "_apply_llm_selection_update_stats_and_budget")
