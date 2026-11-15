import io
import pytest
from app.domains.documents import extract_text_from_file


def test_extract_text_txt():
    content = b"Sample plain text content for testing."
    result = extract_text_from_file("notes.txt", content)
    assert "Sample plain text" in result


def test_extract_text_docx():
    import docx
    doc = docx.Document()
    doc.add_paragraph("First paragraph from docx")
    doc.add_paragraph("Second paragraph from docx")
    buffer = io.BytesIO()
    doc.save(buffer)
    data = buffer.getvalue()

    result = extract_text_from_file("test.docx", data)
    assert "First paragraph from docx" in result
    assert "Second paragraph from docx" in result


def test_extract_text_unsupported():
    with pytest.raises(Exception) as excinfo:
        extract_text_from_file("file.xyz", b"some bytes")
    assert "Unsupported file format" in str(excinfo.value)
