"""Presentation parsing tools."""

from .presentation_parser import CorruptedPresentationError, parse_presentation
from .tool_extract_presentation_slides import (
    DEFAULT_PRESENTATIONS_DIR,
    DEFAULT_SOURCE_FILES,
    ExtractPresentationSlidesSchema,
    extract_presentation_slides,
)

__all__ = [
    "DEFAULT_PRESENTATIONS_DIR",
    "DEFAULT_SOURCE_FILES",
    "CorruptedPresentationError",
    "ExtractPresentationSlidesSchema",
    "extract_presentation_slides",
    "parse_presentation",
]
