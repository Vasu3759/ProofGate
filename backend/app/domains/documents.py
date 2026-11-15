import io
from fastapi import HTTPException


def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract clean text content from PDF, DOCX, TXT, or MD files."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "txt" or ext == "md":
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

    elif ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
            extracted = "\n\n".join(pages)
            if not extracted.strip():
                raise HTTPException(status_code=400, detail="The uploaded PDF contains no readable text or is image-only.")
            return extracted
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF document: {str(e)}")

    elif ext == "docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            extracted = "\n\n".join(paragraphs)
            if not extracted.strip():
                raise HTTPException(status_code=400, detail="The uploaded Word document contains no readable text.")
            return extracted
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to parse Word document: {str(e)}")

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{ext}'. Supported formats are: .pdf, .docx, .txt, .md",
        )
