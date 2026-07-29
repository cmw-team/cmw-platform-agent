"""Model selection tab for the Gradio interface."""

from collections.abc import Callable
import logging
from typing import Any

import gradio as gr

from agent_ng.i18n_translations import get_translation_key


class ConfigTab:
    """Tab that exposes only the primary and fallback LLM selectors."""

    def __init__(
        self,
        event_handlers: dict[str, Callable],
        language: str = "en",
        i18n_instance: gr.I18n | None = None,
    ) -> None:
        self.event_handlers = event_handlers
        self.components: dict[str, Any] = {}
        self.main_app: Any = None
        self.sidebar_instance: Any = None
        self.language = language
        self.i18n = i18n_instance

    def create_tab(self) -> tuple[gr.TabItem, dict[str, Any]]:
        """Build the model-selection tab."""
        logging.getLogger(__name__).info(
            "✅ ConfigTab: Creating model selection interface..."
        )

        with gr.TabItem(self._get_translation("tab_model"), id="config") as tab:
            self._create_config_interface()
            self._connect_events()

        logging.getLogger(__name__).info(
            "✅ ConfigTab: Successfully created model selection interface"
        )
        return tab, self.components

    def _create_config_interface(self) -> None:
        """Create only the shared primary/fallback model controls."""
        if self.sidebar_instance is not None:
            self.sidebar_instance.mount_llm_selection_ui()
        else:
            gr.Markdown("*LLM selection unavailable (internal).*")

        self.components["config_status_display"] = gr.Markdown("")

    def _connect_events(self) -> None:
        """Model control events are wired by the shared Sidebar instance."""

    def set_main_app(self, main_app: Any) -> None:
        """Set the main application reference."""
        self.main_app = main_app

    def set_sidebar_instance(self, sidebar: Any) -> None:
        """Share the Sidebar instance whose model controls render in this tab."""
        self.sidebar_instance = sidebar

    def get_components(self) -> dict[str, Any]:
        """Return created components."""
        return self.components

    def _get_translation(self, key: str) -> str:
        """Get a translation for the active interface language."""
        return get_translation_key(key, self.language)

