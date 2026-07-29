"""
Internationalization (i18n) Translations for CMW Platform Agent
================================================================

Provides Russian and English translations for all UI text in the Gradio application.
Uses Gradio's built-in I18n class for seamless localization support.

Based on Gradio's internationalization documentation:
https://www.gradio.app/guides/internationalization
"""

from typing import Any

import gradio as gr

# Russian translations for all UI text
RUSSIAN_TRANSLATIONS = {
    # Language detection resource (fake resource for Gradio I18n)
    "language": "ru",
    # App title and header
    "app_title": "Помощник продаж и маркетинга Comindware",
    "hero_title": "Помощник продаж и маркетинга",
    # Tab labels
    "tab_home": "🏠 Главная",
    "tab_chat": "💬 Чат",
    "tab_stats": "📊 Статистика",
    "tab_model": "🤖 Модель",
    "tab_sidebar": "⚙️ Настройки и управление",
    "tab_downloads": "📥 Загрузки",
    # Home tab content
    "welcome_title": "Добро пожаловать!",
    "welcome_description": """
    **Помощник продаж и маркетинга Comindware** работает с сущностями **Comindware Platform** — лидами, сделками, кампаниями, сегментами, активностями — и помогает автоматизировать процессы отдела продаж и маркетинга на low-code платформе.

    **Основные возможности:**
    - **Квалификация**: Составление вопросов для аудита.
    - **Пересказ встречь**: Транскрибация и суммаризация встреч с клиентами.
    - **Анализ презентаций**: Анализ презентаций и составление рекомендаций по их улучшению.
    """,
    "quick_start_title": "Быстрый старт",
    "quick_start_description": """
     1. Выберите LLM на вкладке «**Модель**».
     2. Перейдите на вкладку «**Чат**» для начала разговора.
     3. Введите свой вопрос или выберите **заготовку** в левой панели и отредактируйте её, например:
        - Что ты умеешь?
        - Чего ты не умеешь?
        - Составь вопросы для аудита лида 109495.
        - Дай краткое содержание встречи с клиентом.
     4. Нажмите кнопку «**Отправить**» и дождитесь ответа агента.
     5. Агент может отвечать некоторое время.
     6. По окончании работы агент выдаст сообщение «Обработка завершена» в левой панели.
    """,
    # Quick actions
    "quick_audit_questions": "Подготовить вопросы к аудиту",
    "quick_video_transcribation": "Пересказать сореджимое видео",
    "quick_pptx": "Получить рекомендации к презентации",
    "quick_what_can_do": "❓ Что ты умеешь?",
    "quick_what_cannot_do": "❌ Чего ты не умеешь?",
    # History compression
    "compression_enabled_label": "При переполнении сжимать диалог",
    # Chat interface
    "chat_label": "Диалог с агентом",
    "message_label": "Ваше сообщение",
    "message_placeholder": "Введите сообщение или /<навык>...",
    "skill_popup_label": "Команды навыков",
    "skill_popup_hint": "Выберите навык — он загрузится в контекст.",
    "skill_popup_hint_message": "💡 Введите `/` для выбора навыка",
    "send_button": "Отправить",
    "stop_button": "⏹️ Остановить",
    "clear_button": "Очистить диалог",
    "download_button": "📥 Скачать диалог (Markdown)",
    "download_html_button": "🌐 Скачать диалог (HTML)",
    "download_artifacts_zip_button": "📦 Скачать артефакты (ZIP)",
    "download_file_label": "Скачать Markdown",
    # LLM Selection section
    "llm_selection_title": "Выберите LLM",
    "provider_label": "Провайдер",
    "model_label": "Модель",
    "provider_model_label": "Провайдер / модель",
    "apply_llm_button": "Применить",
    "llm_apply_success": "✅ LLM изменена: {provider} - {model}",
    "llm_apply_error": "❌ Ошибка применения LLM",
    # Mistral switching confirmation
    "mistral_switch_title": "⚠️ Внимание! Переключение на Mistral",
    "mistral_switch_warning": """
    Идёт переключение на {provider} / {model}

    Mistral не совместима с другими нейросетями.
    Для продолжения работы чат был очищен.
    """,
    "mistral_chat_cleared": "Чат очищен для совместимости с Mistral.",
    "mistral_switch_cancelled": "❌ Переключение на Mistral отменено",
    "streaming_interrupted": "⚡ Ответ прерван",
    "current_provider": "Провайдер: {provider}",
    "current_model": "Модель: {model}",
    "model_pricing_label": "Цена",
    "model_pricing_input_label": "Ввод",
    "model_pricing_output_label": "Вывод",
    # Status section
    "status_title": "Статус",
    "status_initializing": "🟡 Инициализация...",
    "status_ready": "Готов",
    "status_ready_true": "Готов: да ✅",
    "status_ready_false": "Готов: нет ❌",
    # Status icons for internal token accounting
    "token_status_good": "🟢",
    "token_status_moderate": "🟡",
    "token_status_warning": "🟠",
    "token_status_critical": "🔴",
    "token_status_unknown": "❓",
    "progress_title": "Прогресс",
    "progress_ready": "Готов к работе…",
    "progress_processing": "Обработка запроса...",
    # Turn summary translations
    "conversation_summary": "Сводка диалога",
    "roles_sequence": "Роли",
    "tools_used_total": "Инструменты",
    "providers_models_total": "Провайдеры / модели",
    # Stats tab
    "stats_title": "Статистика агента",
    "stats_loading": "Загрузка статистики...",
    "refresh_stats_button": "🔄 Обновить статистику",
    "clear_stats_button": "🗑️ Очистить статистику",
    "stats_cleared": "Статистика очищена",
    "agent_not_available": "Агент недоступен",
    "stats_auto_refresh_message": "📊 Статистика обновляется автоматически. Нажмите кнопку обновления для просмотра данных сессии.",
    "error_loading_stats": "Ошибка загрузки статистики",
    # Status messages
    "agent_ready": "✅ **Агент готов**",
    "agent_initializing": "🟡 **Инициализация агента...**",
    "agent_not_ready": "❌ **Агент не готов. Пожалуйста, дождитесь завершения инициализации.**",
    # Error messages
    "error_processing": "❌ **Ошибка обработки сообщения: {error}**",
    "error_streaming": "❌ **Ошибка потоковой передачи сообщения: {error}**",
    "error_agent_timeout": "❌ **Таймаут инициализации агента**",
    "error_initialization_failed": "❌ **Ошибка инициализации: {error}**",
    # Token and execution info
    "conversation_cost": "**Стоимость диалога:** {cost}",
    "total_cost": "**Итого:** {cost}",
    "cost_label": "стоимость: {cost}",
    "last_turn_cost": "Последний запрос: {cost}",
    "input_tokens_label": "**Входные токены:** {tokens:,}",
    "output_tokens_label": "**Выходные токены:** {tokens:,}",
    "provider_model_line": "🤖 **Модель:** {provider} / {model}",
    "no_content_response": "⚠️ **Нет ответа от агента.** Попробуйте ещё раз, измените формулировку или переключите модель.",
    # Agent status details
    "agent_status_ready": "✅ **Агент готов**",
    "agent_status_initializing": "🟡 **Инициализация агента**",
    "provider_info": "Провайдер: {provider}",
    "model_info": "**Модель:** {model}",
    "status_label": "**Статус:** {status}",
    "tools_count_label": "**Инструменты:** {count} доступно",
    "last_used_label": "**Последнее использование:** {time}",
    "healthy_status": "✅ Исправен",
    "unhealthy_status": "❌ Неисправен",
    # Statistics labels
    "agent_status_section": "**Агент:**",
    "conversation_section": "**Диалог:**",
    "token_usage_section": "**Использование токенов:**",
    "cost_section": "**Стоимость:**",
    "token_usage_overall": "Всего (все диалоги): {total_tokens:,}",
    "avg_tokens_per_message_label": "Среднее на сообщение: {avg:,}",
    "tools_section": "**Инструменты:**",
    "messages_label": "Сообщения",
    "user_messages_label": "Пользователь",
    "assistant_messages_label": "Ассистент",
    "total_messages_label": "Всего сообщений",
    "available_label": "Доступно",
    "used_label": "Использовано",
    "unique_tools_label": "уникальных",
    "total_calls_label": "Инструменты",
    "tools_used_label": "Использовано инструментов",
    "tools_label": "Инструментов",
    "system_prompt_label": "Система",
    "memory_entries": "Записей в памяти: {count}",
    # Quick action messages
    "quick_audit_questions_message": "/cmw-prepare-lead-questions Составь вопросы для аудита лида {id лида из CRM}",
    "quick_video_transcribation_message": "/cmw-summarize-meeting Перескажи содержимое встречи с клиентом",
    "quick_pptx_message": "/cmw-plan-sales-presentation Как мне улучшить данную презентацию?",
    "quick_what_can_do_message": "Что ты умеешь?",
    "quick_what_cannot_do_message": "Чего ты не умеешь?",
    # Status messages
    "processing_complete": "🎉Обработка завершена",
    "response_completed": "Ответ завершен",
    "processing_failed": "Обработка не удалась",
    # Initialization messages
    "session_manager_ready": "Менеджер сессий готов",
    # Iteration messages
    "iteration_processing": "Итерация {iteration}/{max_iterations} - Обработка...",
    "iteration_finished": "Итерация {iteration}/{max_iterations} - Завершена",
    "iteration_completed": "Итерация {iteration} завершена - Продолжение...",
    "iteration_max_reached": "Итерация {iteration}/{max_iterations} - Завершена (достигнут максимум)",
    "max_iterations_warning": "⚠️ Достигнут лимит итераций ({max_iterations}), диалог может быть неполным",
    # Tool messages
    "tool_called": "🔧 Вызван инструмент: {tool_name}",
    "generating_answer": "✨ Формирую ответ",
    "generating_answer_subtitle": "Готовлю финальный ответ...",
    "call_count": "Количество вызовов: {total_calls}",
    "result": "**Результат:** {tool_result}",
    "tool_error": "❌ **Ошибка инструмента: {error}**",
    "unknown_tool": "❌ **Неизвестный инструмент: {tool_name}**",
    "tools_available": "🔧 Доступно инструментов: {count}",
    "tool_calls_made": "Вызовы инструментов: {tool_names}",
    # Error messages
    "error": "❌ **Ошибка: {error}**",
    # Provider availability messages
    "no_providers_available": "❌ Нет доступных провайдеров",
    "no_models_available": "❌ Нет доступных моделей",
    "error_loading_providers": "❌ Ошибка загрузки провайдеров",
    # History compression
    "history_compression_title": "📦 История диалога сжата",
    "history_compression_info": "Сохранено ~{tokens_saved:,} токенов. Использование: {previous_pct:.1f}% → {current_pct:.1f}%. Сжатий: {compression_count}.",
    "history_compression_info_before": "Сжимаю диалог... ({previous_pct:.1f}% использовано)",
    "history_compression_reason_critical": "Критическое использование токенов (≥90%)",
    "history_compression_reason_proactive": "Сжимаю диалог для предотвращения переполнения",
    "history_compression_reason_interrupted": "Оборванный ход с критическим статусом",
    "compression_stats_label": "Статистика сжатия",
    "compression_count_label": "Сжатий: {count}",
    "compression_tokens_saved_label": "Токенов сохранено: {tokens:,}",
    "use_fallback_model_label": "При переполнении сменить модель",
    # UI Icons
    "clock_icons": [
        "🕐",
        "🕑",
        "🕒",
        "🕓",
        "🕔",
        "🕕",
        "🕖",
        "🕗",
        "🕘",
        "🕙",
        "🕚",
        "🕛",
    ],
    "finish_icons": ["🎉", "🏁", "✨", "🎯"],
    "completion_icons": ["✅", "✔️", "🎯", "✨"],
    "max_icons": ["⚠️", "⏰", "🔄", "⚡"],
    "completion_final_icons": ["✅", "🎯", "✨", "🏆"],
    "error_icons": ["❌", "💥", "⚠️", "🚫"],
}

# English translations (fallback)
ENGLISH_TRANSLATIONS = {
    # Language detection resource (fake resource for Gradio I18n)
    "language": "en",
    # App title and header
    "app_title": "Comindware Analyst Copilot",
    "hero_title": "Analyst Copilot",
    # Tab labels
    "tab_home": "🏠 Home",
    "tab_chat": "💬 Chat",
    "tab_stats": "📊 Statistics",
    "tab_model": "🤖 Model",
    "tab_sidebar": "⚙️ Settings & Control",
    "tab_downloads": "📥 Downloads",
    # Home tab content
    "welcome_title": "Welcome!",
    "welcome_description": """
    **Comindware Analyst Copilot** is designed to work with **Comindware Platform** entities such as applications, templates, and attributes.

    The Copilot uses deterministic tools that do not rely on language models but interact with **Comindware Platform** APIs.

    **Key Features:**
    - **Entity Analysis**: Deep analysis of applications, templates, and attributes in **Comindware Platform**.
    - **Attribute Management**: Creating, editing, and deleting attributes of all types.
    - **Localization**: The agent responds in the language of the question, but can maintain conversations in any language supported by the selected model. Internal reasoning is performed in English. The agent can create entity names in any language. The interface is translated into English and Russian languages.
    """,
    "quick_start_title": "Quick Start",
    "quick_start_description": """
     1. Select an LLM in the **Model** tab.
     2. Go to the **Chat** tab to start a conversation.
     3. Enter your question or select a **template** in the sidebar and edit it, for example:
        - What can you do?
        - What can't you do?
        - List all applications in the platform in a convenient list.
        - Give a full audit of all applications, templates and attributes in the system.
        - Show all record templates in the "ERP" application.
        - Get a list of all attributes of the "Counterparties" template, application "ERP"
        - Create a text attribute "Comment", application "HR", template "Candidates"
        - Create a text attribute "Customer ID", application "ERP", template "Counterparties", special input mask: ([0-9]{10}|[0-9]{12})
        - For the "Contact Phone" attribute in application "CRM", template "Leads", change the display format to Russian phone
        - Get attribute: system name "Comment", application "HR", template "Candidates"
        - Archive/unarchive attribute, system name "Comment", application "HR", template "Candidates"
        - Analyze test_chart.png: what's on the chart and three main takeaways.
        - From application "ERP", template "Counterparties" records, group by category and save infographic platform_infographic.png.
     4. Click **Send** and wait for the agent's response.
     5. The agent may take some time to respond, especially when accessing the **Comindware Platform**. Progress is displayed in the sidebar.
     6. When finished, the agent will show **Processing complete** message in the sidebar.
    """,
    # Quick actions
    "quick_actions_title": "Templates",
    # History compression
    "compression_enabled_label": "Щn overflow сompress conversation",
    "use_fallback_model_label": "On overflow use larger model",
    "quick_list_apps": "🔎 List all apps",
    "quick_create_attr": "🧩 Create text attribute",
    "quick_edit_mask": "🛠️ Edit phone mask",
    "quick_math": "🧮 15 * 23 + 7 = ?",
    "quick_code": "💻 Python prime check function",
    "quick_explain": "💭 Explain ML briefly",
    "quick_full_audit": "🧾 Full system audit",
    # Chat interface
    "chat_label": "Conversation with the Agent",
    "message_label": "Your Message",
    "message_placeholder": "Type a message or /<skill>...",
    "skill_popup_label": "Skill commands",
    "skill_popup_hint": "Pick a skill — it will be loaded into context.",
    "skill_popup_hint_message": "💡 Type `/` to pick a skill",
    "send_button": "Send",
    "stop_button": "⏹️ Stop",
    "clear_button": "Clear conversation",
    "download_button": "📥 Download conversation (Markdown)",
    "download_html_button": "🌐 Download conversation (HTML)",
    "download_artifacts_zip_button": "📦 Download artifacts (ZIP)",
    "download_file_label": "Download Markdown",
    # LLM Selection section
    "llm_selection_title": "Select LLM",
    "provider_label": "Provider",
    "model_label": "Model",
    "provider_model_label": "Provider / model",
    "apply_llm_button": "Apply",
    "llm_apply_success": "✅ LLM changed: {provider} - {model}",
    "llm_apply_error": "❌ Error applying LLM",
    # Mistral switching confirmation
    "mistral_switch_title": "⚠️ Warning! Switching to Mistral",
    "mistral_switch_warning": """
    Switching to {provider} / {model}...

    Mistral is not compatible with other providers.
    The chat was cleared to continue working.
    """,
    "mistral_chat_cleared": "Chat cleared for Mistral compatibility.",
    "mistral_switch_cancelled": "❌ Mistral switching cancelled",
    "streaming_interrupted": "⚡ Response interrupted",
    "current_provider": "Provider: {provider}",
    "current_model": "**Model:** {model}",
    "model_pricing_label": "Pricing",
    "model_pricing_input_label": "Input",
    "model_pricing_output_label": "Output",
    # Status section
    "status_title": "Status",
    "status_initializing": "🟡 Initializing...",
    "status_ready": "Ready",
    "status_ready_true": "Ready: yes ✅",
    "status_ready_false": "Ready: no ❌",
    # Status icons for internal token accounting
    "token_status_good": "🟢",
    "token_status_moderate": "🟡",
    "token_status_warning": "🟠",
    "token_status_critical": "🔴",
    "token_status_unknown": "❓",
    "progress_title": "Progress",
    "progress_ready": "Ready to process your request...",
    "progress_processing": "Processing request...",
    # Turn summary translations
    "conversation_summary": "Conversation summary",
    "roles_sequence": "Roles",
    "tools_used_total": "Tools",
    "providers_models_total": "Providers / models",
    # Stats tab
    "stats_title": "Agent Statistics",
    "stats_loading": "Loading statistics...",
    "refresh_stats_button": "🔄 Refresh Stats",
    "clear_stats_button": "🗑️ Clear Stats",
    "stats_cleared": "Statistics cleared",
    "agent_not_available": "Agent not available",
    "stats_auto_refresh_message": "📊 Statistics are auto-refreshing. Click refresh button to view session data.",
    "error_loading_stats": "Error loading statistics",
    # Status messages
    "agent_ready": "✅ **Agent Ready**",
    "agent_initializing": "🟡 **Agent Initializing**",
    "agent_not_ready": "❌ **Agent not ready. Please wait for initialization to complete.**",
    # Error messages
    "error_processing": "❌ **Error processing message: {error}**",
    "error_streaming": "❌ **Error streaming message: {error}**",
    "error_agent_timeout": "❌ **Agent initialization timeout**",
    "error_initialization_failed": "❌ **Initialization failed: {error}**",
    # Token and execution info
    "conversation_cost": "**Conversation cost:** {cost}",
    "total_cost": "**Total cost:** {cost}",
    "cost_label": "cost: {cost}",
    "last_turn_cost": "Last turn: {cost}",
    "input_tokens_label": "**Input tokens:** {tokens:,}",
    "output_tokens_label": "**Output tokens:** {tokens:,}",
    "provider_model_line": "🤖 **Model:** {provider} / {model}",
    "no_content_response": "⚠️ **No answer from the agent.** Please try again, rephrase, or switch the model.",
    # Agent status details
    "agent_status_ready": "✅ **Agent Ready**",
    "agent_status_initializing": "🟡 **Agent Initializing**",
    "provider_info": "Provider: {provider}",
    "model_info": "**Model:** {model}",
    "status_label": "**Status:** {status}",
    "tools_count_label": "**Tools:** {count} available",
    "last_used_label": "**Last Used:** {time}",
    "healthy_status": "✅ Healthy",
    "unhealthy_status": "❌ Unhealthy",
    # Statistics labels
    "agent_status_section": "**Agent:**",
    "conversation_section": "**Conversation:**",
    "token_usage_section": "**Token Usage:**",
    "cost_section": "**Cost:**",
    "token_usage_overall": "Total (all conversations): {total_tokens:,}",
    "avg_tokens_per_message_label": "Average per message: {avg:,}",
    "tools_section": "**Tools:**",
    "messages_label": "Messages",
    "user_messages_label": "User",
    "assistant_messages_label": "Copilot",
    "total_messages_label": "Total messages",
    "available_label": "Available",
    "used_label": "Used",
    "unique_tools_label": "unique",
    "total_calls_label": "Tools",
    "tools_used_label": "Used tools",
    "tools_label": "Tools",
    "system_prompt_label": "System",
    "memory_entries": "Memory entries: {count}",
    # Query example buttons (converted from try_asking_examples)
    "quick_what_can_do": "❓ What can you do?",
    "quick_what_can_do_message": "What can you do?",
    "quick_what_cannot_do": "❌ What can't you do?",
    "quick_what_cannot_do_message": "What can't you do?",
    # Status messages
    "processing_complete": "🎉 Processing complete",
    "response_completed": "Response completed",
    "processing_failed": "Processing failed",
    # Initialization messages
    "session_manager_ready": "Session manager ready",
    # Iteration messages
    "iteration_processing": "Iteration **{iteration}/{max_iterations}** - Processing...",
    "iteration_finished": "Iteration **{iteration}/{max_iterations}** - Finished",
    "iteration_completed": "Iteration **{iteration}** completed - Continuing...",
    "iteration_max_reached": "Iteration **{iteration}/{max_iterations}** - Finished (max reached)",
    "max_iterations_warning": "⚠️ Reached iteration limit **({max_iterations})**, conversation may be incomplete",
    # Tool messages
    "tool_called": "🔧 Tool called: {tool_name}",
    "generating_answer": "Generating answer",
    "generating_answer_subtitle": "Preparing the final response...",
    "call_count": "Call count: {total_calls}",
    "result": "**Result:** {tool_result}",
    "tool_error": "❌ **Tool error: {error}**",
    "unknown_tool": "❌ **Unknown tool: {tool_name}**",
    "tools_available": "🔧 Tools available: {count}",
    "tool_calls_made": "Tool calls made: {tool_names}",
    # Error messages
    "error": "❌ **Error: {error}**",
    # Provider availability messages
    "no_providers_available": "❌ No providers available",
    "no_models_available": "❌ No models available",
    "error_loading_providers": "❌ Error loading providers",
    # History compression
    "history_compression_title": "📦 Conversation History Compressed",
    "history_compression_info": "Saved ~{tokens_saved:,} tokens. Usage: {previous_pct:.1f}% → {current_pct:.1f}%. Compressions: {compression_count}.",
    "history_compression_info_before": "Compressing conversation... ({previous_pct:.1f}% used)",
    "history_compression_reason_critical": "Critical token usage (≥{threshold}%)",
    "history_compression_reason_proactive": "Compressing conversation to prevent overflow",
    "history_compression_reason_interrupted": "Turn interrupted with critical status",
    "compression_stats_label": "Compression Stats",
    "compression_count_label": "Compressions: {count}",
    "compression_tokens_saved_label": "Tokens saved: {tokens:,}",
    # UI Icons
    "clock_icons": [
        "🕐",
        "🕑",
        "🕒",
        "🕓",
        "🕔",
        "🕕",
        "🕖",
        "🕗",
        "🕘",
        "🕙",
        "🕚",
        "🕛",
    ],
    "finish_icons": ["🎉", "🏁", "✨", "🎯"],
    "completion_icons": ["✅", "✔️", "🎯", "✨"],
    "max_icons": ["⚠️", "⏰", "🔄", "⚡"],
    "completion_final_icons": ["✅", "🎯", "✨", "🏆"],
    "error_icons": ["❌", "💥", "⚠️", "🚫"],
}


def create_i18n_instance() -> gr.I18n:
    """
    Create a Gradio I18n instance with translations for all supported languages.

    Returns:
        Gradio I18n instance with both English and Russian translations
    """
    return gr.I18n(en=ENGLISH_TRANSLATIONS, ru=RUSSIAN_TRANSLATIONS)


def get_translation_key(key: str, language: str = "en") -> str:
    """
    Get a translation for a specific key in the specified language.

    Args:
        key: Translation key
        language: Language code ('en' or 'ru')

    Returns:
        Translated string
    """
    # Safety check for None key
    if key is None:
        return "Unknown"

    # Safety check for None language
    if language is None:
        language = "en"

    if language.lower() == "ru":
        return RUSSIAN_TRANSLATIONS.get(key, ENGLISH_TRANSLATIONS.get(key, key))
    return ENGLISH_TRANSLATIONS.get(key, key)


def format_translation(key: str, language: str = "en", **kwargs: Any) -> str:
    """
    Get a formatted translation for a specific key with variable substitution.

    Args:
        key: Translation key
        language: Language code ('en' or 'ru')
        **kwargs: Variables to substitute in the translation

    Returns:
        Formatted translated string
    """
    # Safety check for None key
    if key is None:
        return "Unknown"

    # Safety check for None language
    if language is None:
        language = "en"

    template = get_translation_key(key, language)
    try:
        return template.format(**kwargs)
    except KeyError as e:
        print(
            f"Warning: Missing format variable {e} for key '{key}' in language '{language}'"
        )
        return template
