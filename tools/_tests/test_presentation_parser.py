"""Behavior tests for the read-only PresentationML parser."""

from __future__ import annotations

import importlib
import json
from textwrap import dedent
from typing import TYPE_CHECKING, Any
import zipfile

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)
NOTES_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
)


def _parser_module():
    return importlib.import_module("tools.presentation_tools.presentation_parser")


def _shape(
    text_paragraphs: tuple[tuple[str, ...], ...],
    *,
    placeholder: str | None = None,
    shape_id: int = 2,
) -> str:
    placeholder_xml = f'<p:ph type="{placeholder}"/>' if placeholder else ""
    paragraphs = "".join(
        "<a:p>"
        + "".join(f"<a:r><a:t>{run}</a:t></a:r>" for run in runs)
        + "</a:p>"
        for runs in text_paragraphs
    )
    return dedent(
        f"""
        <p:sp>
          <p:nvSpPr>
            <p:cNvPr id="{shape_id}" name="Shape {shape_id}"/>
            <p:cNvSpPr/>
            <p:nvPr>{placeholder_xml}</p:nvPr>
          </p:nvSpPr>
          <p:spPr/>
          <p:txBody>
            <a:bodyPr/>
            <a:lstStyle/>
            {paragraphs}
          </p:txBody>
        </p:sp>
        """
    ).strip()


def _table(cell_texts: tuple[str, ...]) -> str:
    cells = "".join(
        f"""
        <a:tc>
          <a:txBody>
            <a:bodyPr/>
            <a:lstStyle/>
            <a:p><a:r><a:t>{text}</a:t></a:r></a:p>
          </a:txBody>
          <a:tcPr/>
        </a:tc>
        """
        for text in cell_texts
    )
    return dedent(
        f"""
        <p:graphicFrame>
          <p:nvGraphicFramePr>
            <p:cNvPr id="20" name="Table"/>
            <p:cNvGraphicFramePr/>
            <p:nvPr/>
          </p:nvGraphicFramePr>
          <p:xfrm/>
          <a:graphic>
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">
              <a:tbl>
                <a:tblPr/>
                <a:tblGrid/>
                <a:tr h="1">{cells}</a:tr>
              </a:tbl>
            </a:graphicData>
          </a:graphic>
        </p:graphicFrame>
        """
    ).strip()


def _picture() -> str:
    return dedent(
        """
        <p:pic>
          <p:nvPicPr>
            <p:cNvPr id="30" name="Picture"/>
            <p:cNvPicPr/>
            <p:nvPr/>
          </p:nvPicPr>
          <p:blipFill/>
          <p:spPr/>
        </p:pic>
        """
    ).strip()


def _chart() -> str:
    return dedent(
        """
        <p:graphicFrame>
          <p:nvGraphicFramePr>
            <p:cNvPr id="40" name="Chart"/>
            <p:cNvGraphicFramePr/>
            <p:nvPr/>
          </p:nvGraphicFramePr>
          <p:xfrm/>
          <a:graphic>
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">
              <c:chart r:id="rIdChart"/>
            </a:graphicData>
          </a:graphic>
        </p:graphicFrame>
        """
    ).strip()


def _slide_xml(*elements: str) -> str:
    content = "\n".join(elements)
    return dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:sld xmlns:p="{P_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:c="{C_NS}">
          <p:cSld>
            <p:spTree>
              <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
              </p:nvGrpSpPr>
              <p:grpSpPr/>
              {content}
            </p:spTree>
          </p:cSld>
        </p:sld>
        """
    ).strip()


def _notes_xml(*elements: str) -> str:
    content = "\n".join(elements)
    return dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:notes xmlns:p="{P_NS}" xmlns:a="{A_NS}">
          <p:cSld>
            <p:spTree>
              <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
              </p:nvGrpSpPr>
              <p:grpSpPr/>
              {content}
            </p:spTree>
          </p:cSld>
        </p:notes>
        """
    ).strip()


def _write_pptx(
    path: Path,
    slides: dict[int, str],
    *,
    order: tuple[int, ...] | None = None,
    notes: dict[int, str] | None = None,
) -> Path:
    ordered_numbers = order or tuple(slides)
    slide_ids = "".join(
        f'<p:sldId id="{255 + index}" r:id="rId{slide_number}"/>'
        for index, slide_number in enumerate(ordered_numbers, start=1)
    )
    presentation = dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:presentation xmlns:p="{P_NS}" xmlns:r="{R_NS}">
          <p:sldIdLst>{slide_ids}</p:sldIdLst>
        </p:presentation>
        """
    ).strip()
    relationships = "".join(
        f'<Relationship Id="rId{number}" Type="{SLIDE_REL}" '
        f'Target="slides/slide{number}.xml"/>'
        for number in slides
    )
    presentation_relationships = (
        f'<Relationships xmlns="{PKG_REL_NS}">{relationships}</Relationships>'
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr(
            "ppt/_rels/presentation.xml.rels", presentation_relationships
        )
        for number, xml in slides.items():
            archive.writestr(f"ppt/slides/slide{number}.xml", xml)
            if notes and number in notes:
                archive.writestr(
                    f"ppt/notesSlides/notesSlide{number}.xml", notes[number]
                )
                archive.writestr(
                    f"ppt/slides/_rels/slide{number}.xml.rels",
                    (
                        f'<Relationships xmlns="{PKG_REL_NS}">'
                        f'<Relationship Id="rIdNotes" Type="{NOTES_REL}" '
                        f'Target="../notesSlides/notesSlide{number}.xml"/>'
                        "</Relationships>"
                    ),
                )
    return path


def test_parse_presentation_uses_declared_slide_order_and_extracts_all_text(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "ordered.pptx",
        {
            1: _slide_xml(_shape((("First physical slide",),))),
            2: _slide_xml(
                _shape((("Declared", " title"),), placeholder="title"),
                _shape((("First paragraph",), ("Second paragraph",)), shape_id=3),
                _table(("Cell A", "Cell B")),
                _picture(),
                _picture(),
                _chart(),
            ),
        },
        order=(2, 1),
    )

    result = parser.parse_presentation(deck)
    expected_text = (
        "Declared title\nFirst paragraph\nSecond paragraph\nCell A\nCell B"
    )

    assert result["slide_count"] == 2
    assert result["slides"][0] == {
        "number": 1,
        "title": "Declared title",
        "title_source": "placeholder",
        "text": expected_text,
        "text_length": len(expected_text),
        "notes": "",
        "objects": {"pictures": 2, "tables": 1, "charts": 1},
        "warnings": [],
    }
    assert result["slides"][1]["number"] == 2
    assert result["slides"][1]["text"] == "First physical slide"


def test_parse_presentation_uses_first_text_as_title_fallback(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "fallback.pptx",
        {1: _slide_xml(_shape((("Fallback heading",), ("Body",))))},
    )

    slide = parser.parse_presentation(deck)["slides"][0]

    assert slide["title"] == "Fallback heading"
    assert slide["title_source"] == "first_text"
    assert slide["warnings"] == []


def test_parse_presentation_extracts_notes_but_ignores_notes_placeholders(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "notes.pptx",
        {1: _slide_xml(_shape((("Title",),), placeholder="title"))},
        notes={
            1: _notes_xml(
                _shape((("Presenter note",),), placeholder="body"),
                _shape((("1",),), placeholder="sldNum", shape_id=3),
                _shape((("Confidential",),), placeholder="ftr", shape_id=4),
            )
        },
    )

    slide = parser.parse_presentation(deck)["slides"][0]

    assert slide["notes"] == "Presenter note"


def test_parse_presentation_keeps_empty_slide_with_objective_warnings(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(tmp_path / "empty.pptx", {1: _slide_xml(_picture())})

    result = parser.parse_presentation(deck)
    slide = result["slides"][0]

    assert slide["title"] == ""
    assert slide["title_source"] == "none"
    assert slide["text"] == ""
    assert slide["warnings"] == ["missing_title", "no_extractable_text"]
    assert result["capabilities"] == {
        "text_extraction_complete": True,
        "visual_content_analyzed": False,
    }


def test_parse_presentation_marks_malformed_slide_as_partial_and_continues(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "partial.pptx",
        {
            1: "<p:sld>",
            2: _slide_xml(_shape((("Healthy slide",),))),
        },
    )

    result = parser.parse_presentation(deck)

    assert result["slide_count"] == 2
    assert result["capabilities"]["text_extraction_complete"] is False
    assert result["slides"][0]["warnings"] == [
        "missing_title",
        "no_extractable_text",
        "partial_extraction",
    ]
    assert result["slides"][1]["text"] == "Healthy slide"


def test_parse_presentation_keeps_slide_text_when_only_notes_are_malformed(
    tmp_path: Path,
) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "malformed-notes.pptx",
        {1: _slide_xml(_shape((("Healthy title",),), placeholder="title"))},
        notes={1: "<p:notes>"},
    )

    result = parser.parse_presentation(deck)
    slide = result["slides"][0]

    assert slide["title"] == "Healthy title"
    assert slide["text"] == "Healthy title"
    assert slide["notes"] == ""
    assert slide["warnings"] == ["partial_extraction"]
    assert result["capabilities"]["text_extraction_complete"] is False


@pytest.mark.parametrize(
    "file_builder",
    [
        lambda path: path.write_text("not a zip", encoding="utf-8"),
        lambda path: zipfile.ZipFile(path, "w").close(),
    ],
)
def test_parse_presentation_rejects_corrupted_package(
    tmp_path: Path,
    file_builder: Callable[[Path], Any],
) -> None:
    parser = _parser_module()
    deck = tmp_path / "corrupted.pptx"
    file_builder(deck)

    with pytest.raises(parser.CorruptedPresentationError):
        parser.parse_presentation(deck)


def test_parse_presentation_result_is_json_serializable(tmp_path: Path) -> None:
    parser = _parser_module()
    deck = _write_pptx(
        tmp_path / "serializable.pptx",
        {1: _slide_xml(_shape((("Title",),), placeholder="title"))},
    )

    result = parser.parse_presentation(deck)

    json.dumps(result, ensure_ascii=False)
