"""Tests for the i18n keys added for the slash-command popup."""

from __future__ import annotations


def test_message_placeholder_mentions_slash_in_en() -> None:
    from agent_ng.i18n_translations import get_translation_key

    placeholder = get_translation_key("message_placeholder", "en")
    assert "/<skill>" in placeholder


def test_message_placeholder_mentions_slash_in_ru() -> None:
    from agent_ng.i18n_translations import get_translation_key

    placeholder = get_translation_key("message_placeholder", "ru")
    assert "/<" in placeholder


def test_skill_popup_label_en() -> None:
    from agent_ng.i18n_translations import get_translation_key

    assert get_translation_key("skill_popup_label", "en") == "Skill commands"


def test_skill_popup_label_ru() -> None:
    from agent_ng.i18n_translations import get_translation_key

    assert get_translation_key("skill_popup_label", "ru") == "Команды навыков"


def test_skill_popup_hint_non_empty_en() -> None:
    from agent_ng.i18n_translations import get_translation_key

    assert get_translation_key("skill_popup_hint", "en")


def test_skill_popup_hint_non_empty_ru() -> None:
    from agent_ng.i18n_translations import get_translation_key

    assert get_translation_key("skill_popup_hint", "ru")


def test_skill_popup_hint_message_en_mentions_slash() -> None:
    from agent_ng.i18n_translations import get_translation_key

    msg = get_translation_key("skill_popup_hint_message", "en")
    assert "/" in msg


def test_skill_popup_hint_message_ru_mentions_slash() -> None:
    from agent_ng.i18n_translations import get_translation_key

    msg = get_translation_key("skill_popup_hint_message", "ru")
    assert "/" in msg
