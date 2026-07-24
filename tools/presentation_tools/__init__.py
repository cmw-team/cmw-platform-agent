"""Presentation parsing tools."""

from .presentation_parser import CorruptedPresentationError, parse_presentation

__all__ = ["CorruptedPresentationError", "parse_presentation"]
