"""Read-only PresentationML parser.

The parser reads known OOXML parts directly from a PPTX ZIP package. It never
extracts archive entries to disk, calls external services, or mutates the source.
"""

from __future__ import annotations

import logging
from pathlib import Path
import posixpath
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

logger = logging.getLogger(__name__)

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

PRESENTATION_PART = "ppt/presentation.xml"
R_ID = f"{{{R_NS}}}id"

P_SLD_ID = f"{{{P_NS}}}sldId"
P_SP = f"{{{P_NS}}}sp"
P_PH = f"{{{P_NS}}}ph"
P_PIC = f"{{{P_NS}}}pic"
A_P = f"{{{A_NS}}}p"
A_T = f"{{{A_NS}}}t"
A_TBL = f"{{{A_NS}}}tbl"
C_CHART = f"{{{C_NS}}}chart"
RELATIONSHIP = f"{{{PKG_REL_NS}}}Relationship"

TITLE_PLACEHOLDERS = frozenset({"title", "ctrTitle"})
IGNORED_NOTES_PLACEHOLDERS = frozenset(
    {"dt", "ftr", "hdr", "sldImg", "sldNum"}
)

MAX_PACKAGE_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_XML_PART_BYTES = 16 * 1024 * 1024


class CorruptedPresentationError(ValueError):
    """Raised when a file is not a readable PresentationML package."""


def _relationship_part_name(part_name: str) -> str:
    directory, filename = posixpath.split(part_name)
    return posixpath.join(directory, "_rels", f"{filename}.rels")


def _resolve_target(part_name: str, target: str) -> str:
    if target.startswith("/"):
        resolved = posixpath.normpath(target.lstrip("/"))
    else:
        resolved = posixpath.normpath(
            posixpath.join(posixpath.dirname(part_name), target)
        )
    if resolved == ".." or resolved.startswith("../") or ":" in resolved:
        raise CorruptedPresentationError("Unsafe relationship target")
    return resolved


def _read_part(archive: zipfile.ZipFile, part_name: str) -> bytes:
    try:
        info = archive.getinfo(part_name)
    except KeyError as exc:
        message = f"Required presentation part is missing: {part_name}"
        raise CorruptedPresentationError(message) from exc
    if info.file_size > MAX_XML_PART_BYTES:
        message = f"Presentation XML part is too large: {part_name}"
        raise CorruptedPresentationError(message)
    return archive.read(info)


def _parse_xml_part(archive: zipfile.ZipFile, part_name: str) -> ET.Element:
    try:
        # Demo deployment: inputs are limited to a restricted internal network.
        # Package and part size limits above reduce resource-exhaustion risk.
        return ET.fromstring(_read_part(archive, part_name))  # noqa: S314
    except ET.ParseError as exc:
        message = f"Presentation XML part is malformed: {part_name}"
        raise CorruptedPresentationError(message) from exc


def _relationship_targets(
    archive: zipfile.ZipFile,
    part_name: str,
) -> dict[str, tuple[str, str]]:
    relationships_name = _relationship_part_name(part_name)
    if relationships_name not in archive.namelist():
        return {}
    relationships_root = _parse_xml_part(archive, relationships_name)

    targets: dict[str, tuple[str, str]] = {}
    for relationship in relationships_root.iter(RELATIONSHIP):
        relationship_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        relationship_type = relationship.attrib.get("Type", "")
        target_mode = relationship.attrib.get("TargetMode", "")
        if (
            not relationship_id
            or not target
            or target_mode.casefold() == "external"
        ):
            continue
        targets[relationship_id] = (
            relationship_type,
            _resolve_target(part_name, target),
        )
    return targets


def _paragraphs(root: ET.Element) -> list[str]:
    values: list[str] = []
    for paragraph in root.iter(A_P):
        text = "".join(node.text or "" for node in paragraph.iter(A_T)).strip()
        if text:
            values.append(text)
    return values


def _shape_paragraphs(shape: ET.Element) -> list[str]:
    return _paragraphs(shape)


def _title(root: ET.Element, paragraphs: list[str]) -> tuple[str, str]:
    for shape in root.iter(P_SP):
        placeholder = shape.find(f".//{P_PH}")
        if (
            placeholder is not None
            and placeholder.attrib.get("type") in TITLE_PLACEHOLDERS
        ):
            title = "\n".join(_shape_paragraphs(shape)).strip()
            if title:
                return title, "placeholder"
    if paragraphs:
        return paragraphs[0], "first_text"
    return "", "none"


def _notes(
    archive: zipfile.ZipFile,
    slide_part: str,
) -> str:
    for relationship_type, target in _relationship_targets(
        archive, slide_part
    ).values():
        if not relationship_type.endswith("/notesSlide"):
            continue
        notes_root = _parse_xml_part(archive, target)
        paragraphs: list[str] = []
        for shape in notes_root.iter(P_SP):
            placeholder = shape.find(f".//{P_PH}")
            placeholder_type = (
                placeholder.attrib.get("type") if placeholder is not None else None
            )
            if placeholder_type in IGNORED_NOTES_PLACEHOLDERS:
                continue
            paragraphs.extend(_shape_paragraphs(shape))
        return "\n".join(paragraphs)
    return ""


def _empty_slide(number: int, *, partial: bool) -> dict[str, Any]:
    warnings = ["missing_title", "no_extractable_text"]
    if partial:
        warnings.append("partial_extraction")
    return {
        "number": number,
        "title": "",
        "title_source": "none",
        "text": "",
        "text_length": 0,
        "notes": "",
        "objects": {"pictures": 0, "tables": 0, "charts": 0},
        "warnings": warnings,
    }


def _parse_slide(
    archive: zipfile.ZipFile,
    slide_part: str,
    number: int,
) -> dict[str, Any]:
    root = _parse_xml_part(archive, slide_part)
    paragraphs = _paragraphs(root)
    text = "\n".join(paragraphs)
    title, title_source = _title(root, paragraphs)
    warnings: list[str] = []
    if not title:
        warnings.append("missing_title")
    if not text:
        warnings.append("no_extractable_text")
    try:
        notes = _notes(archive, slide_part)
    except CorruptedPresentationError as exc:
        logger.warning(
            "Partial PPTX notes extraction for slide %d: %s", number, exc
        )
        notes = ""
        warnings.append("partial_extraction")

    return {
        "number": number,
        "title": title,
        "title_source": title_source,
        "text": text,
        "text_length": len(text),
        "notes": notes,
        "objects": {
            "pictures": sum(1 for _ in root.iter(P_PIC)),
            "tables": sum(1 for _ in root.iter(A_TBL)),
            "charts": sum(1 for _ in root.iter(C_CHART)),
        },
        "warnings": warnings,
    }


def _ordered_slide_parts(archive: zipfile.ZipFile) -> list[str]:
    presentation_root = _parse_xml_part(archive, PRESENTATION_PART)
    relationships = _relationship_targets(archive, PRESENTATION_PART)
    parts: list[str] = []
    for slide_id in presentation_root.iter(P_SLD_ID):
        relationship_id = slide_id.attrib.get(R_ID)
        relationship = relationships.get(relationship_id or "")
        if relationship is None or not relationship[0].endswith("/slide"):
            raise CorruptedPresentationError(
                "Presentation slide relationship is missing"
            )
        parts.append(relationship[1])
    return parts


def _validate_package_size(archive: zipfile.ZipFile) -> None:
    total_size = sum(info.file_size for info in archive.infolist())
    if total_size > MAX_PACKAGE_UNCOMPRESSED_BYTES:
        raise CorruptedPresentationError(
            "Presentation package exceeds the uncompressed size limit"
        )


def parse_presentation(file_path: str | Path) -> dict[str, Any]:
    """Extract structured text and metadata from every slide in a PPTX file."""
    path = Path(file_path)
    try:
        with zipfile.ZipFile(path) as archive:
            _validate_package_size(archive)
            slide_parts = _ordered_slide_parts(archive)
            slides: list[dict[str, Any]] = []
            extraction_complete = True
            for number, slide_part in enumerate(slide_parts, start=1):
                try:
                    slide = _parse_slide(archive, slide_part, number)
                    if "partial_extraction" in slide["warnings"]:
                        extraction_complete = False
                    slides.append(slide)
                except CorruptedPresentationError as exc:
                    extraction_complete = False
                    logger.warning(
                        "Partial PPTX extraction for slide %d: %s", number, exc
                    )
                    slides.append(_empty_slide(number, partial=True))
    except (zipfile.BadZipFile, OSError) as exc:
        raise CorruptedPresentationError(
            "File is not a readable PPTX package"
        ) from exc

    return {
        "slide_count": len(slides),
        "capabilities": {
            "text_extraction_complete": extraction_complete,
            "visual_content_analyzed": False,
        },
        "slides": slides,
    }


__all__ = ["CorruptedPresentationError", "parse_presentation"]
