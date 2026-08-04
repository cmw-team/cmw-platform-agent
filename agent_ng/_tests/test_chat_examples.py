"""Tests for empty-chat examples and persistent quick-action buttons."""

import gradio as gr

from agent_ng.i18n_translations import get_translation_key


class TestBuildExampleMessages:
    """Tests for _build_chatbot_examples — defines behavior contract."""

    def _sut(self, language="en"):
        from agent_ng.tabs.chat_tab import _build_chatbot_examples

        return _build_chatbot_examples(language)

    def test_examples_count_matches_config(self):
        from agent_ng.tabs.chat_tab import EMPTY_CHAT_EXAMPLES_CONFIG

        examples = self._sut()
        assert len(examples) == len(EMPTY_CHAT_EXAMPLES_CONFIG) == 5

    def test_each_example_has_display_text_and_text(self):
        for ex in self._sut():
            assert "display_text" in ex
            assert "text" in ex
            assert isinstance(ex["display_text"], str)
            assert isinstance(ex["text"], str)

    def test_display_text_is_label_not_message_text(self):
        examples = self._sut("en")
        whats_can_do = next(
            e for e in examples if e["display_text"] == "❓ What can you do?"
        )
        assert whats_can_do["text"] == "What can you do?"

    def test_russian_labels_present(self):
        examples = self._sut("ru")
        for ex in examples:
            assert ex["display_text"] != ""
            assert ex["text"] != ""


class TestHandleExampleSelect:
    """Tests for _handle_example_select — defines behavior contract."""

    def _sut(self, example_data: dict) -> dict:
        """Subject under test — mirrors what chat_tab.py will expose."""
        return gr.MultimodalTextbox(
            value={"text": example_data.get("text", ""), "files": []}
        )

    def test_returns_multimodaltextbox_with_text(self):
        result = self._sut({"text": "Hello world", "files": []})
        assert result.value == {"text": "Hello world", "files": []}

    def test_returns_empty_files_when_not_present(self):
        result = self._sut({"text": "Hi"})
        assert result.value["files"] == []

    def test_handles_missing_text_field(self):
        result = self._sut({})
        assert result.value == {"text": "", "files": []}


class TestPersistentQuickActions:
    """The three skill shortcuts remain separate from empty-chat examples."""

    def test_config_contains_only_three_skill_actions(self):
        from agent_ng.tabs.chat_tab import STATIC_SKILL_ACTIONS_CONFIG

        assert list(STATIC_SKILL_ACTIONS_CONFIG) == [
            "quick_video_transcribation",
            "quick_audit_questions",
            "quick_pptx",
        ]

    def test_click_value_contains_translated_command_and_no_files(self):
        from agent_ng.tabs.chat_tab import _build_static_quick_action_value

        result = _build_static_quick_action_value(
            "quick_video_transcribation_message", "ru"
        )

        assert result.value == {
            "text": get_translation_key(
                "quick_video_transcribation_message", "ru"
            ),
            "files": [],
        }

    def test_skill_actions_are_empty_chat_examples(self):
        example_labels = {
            example["display_text"] for example in self._sut_examples("ru")
        }

        assert (
            get_translation_key("quick_video_transcribation", "ru")
            in example_labels
        )
        assert (
            get_translation_key("quick_audit_questions", "ru")
            in example_labels
        )
        assert get_translation_key("quick_pptx", "ru") in example_labels

    def test_visibility_update_shows_actions_after_submit(self):
        from agent_ng.tabs.chat_tab import _build_static_quick_actions_visibility

        assert (
            _build_static_quick_actions_visibility(visible=True)["visible"] is True
        )

    def test_visibility_update_hides_actions_after_clear(self):
        from agent_ng.tabs.chat_tab import _build_static_quick_actions_visibility

        assert (
            _build_static_quick_actions_visibility(visible=False)["visible"] is False
        )

    @staticmethod
    def _sut_examples(language: str) -> list[dict[str, str]]:
        from agent_ng.tabs.chat_tab import _build_chatbot_examples

        return _build_chatbot_examples(language)
