"""
Shared copy text used by record document / image tool ``@tool`` descriptions.

After the 2026-07 cleanup, ``tools.templates_tools.tool_record_document`` and
``tools.templates_tools.tool_record_image`` were removed (along with their
``platform_record_document`` / ``platform_record_image`` helpers). The constants
below have no live consumers in the current tool surface but are kept as inert
text for any future record-document / record-image tool that may be reintroduced.

Generic field reads continue to use ``tool_get_record_values`` (``get_record_values``).
"""

# Pydantic ``Field(description=...)`` for **filename** (e.g. **attach** tools).
CHAT_FILENAME_DESCRIPTION = (
    "Which file to work with. Use the **name with extension** the user put in this chat, **or** "
    "a **https** (or **http**) **URL** to a public file on the web."
)

# Reused when composing the **fetch** @tool description in each record tool module.
CHAT_FILENAME_RESULT_HINT = (
    "On success you get a **``filename``** string. Pass that **same** string to the next "
    "file or text tool; do not substitute a made-up or guessed name."
)
