"""
PDF parsing using pdfplumber and pypdf as fallback
"""

import logging
from typing import Optional
import pdfplumber
import pypdf

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDF CVs with pdfplumber (primary) and pypdf (fallback)"""

    def __init__(self):
        self.logger = logger

    def parse(self, file_path: str) -> Optional[str]:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text or None if parsing fails
        """
        # Try pdfplumber first (better for complex layouts)
        text = self._parse_with_pdfplumber(file_path)

        if not text or len(text.strip()) < 100:
            # Fallback to pypdf
            self.logger.warning(f"pdfplumber extraction poor, trying pypdf fallback")
            text = self._parse_with_pypdf(file_path)

        return text

    def _parse_with_pdfplumber(self, file_path: str) -> Optional[str]:
        """Parse PDF using pdfplumber"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_parts = []

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text from page
                        page_text = page.extract_text()

                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n")
                            text_parts.append(page_text)
                            text_parts.append("\n\n")

                        # Extract tables separately (better formatting)
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables):
                                text_parts.append(f"[Table {table_idx + 1}]\n")
                                for row in table:
                                    if row:
                                        text_parts.append(" | ".join(str(cell or "") for cell in row))
                                        text_parts.append("\n")
                                text_parts.append("\n")

                    except Exception as e:
                        self.logger.warning(f"Error extracting page {page_num}: {e}")
                        continue

                return "".join(text_parts)

        except Exception as e:
            self.logger.error(f"pdfplumber parsing failed: {e}")
            return None

    def _parse_with_pypdf(self, file_path: str) -> Optional[str]:
        """Parse PDF using pypdf as fallback"""
        try:
            with open(file_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                text_parts = []

                for page_num, page in enumerate(reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"--- Page {page_num} ---\n")
                            text_parts.append(text)
                            text_parts.append("\n\n")
                    except Exception as e:
                        self.logger.warning(f"Error extracting page {page_num}: {e}")
                        continue

                return "".join(text_parts)

        except Exception as e:
            self.logger.error(f"pypdf parsing failed: {e}")
            return None

    def get_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata"""
        metadata = {}

        try:
            with open(file_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                info = reader.metadata

                if info:
                    metadata = {
                        "title": info.get("/Title", ""),
                        "author": info.get("/Author", ""),
                        "creator": info.get("/Creator", ""),
                        "producer": info.get("/Producer", ""),
                        "creation_date": str(info.get("/CreationDate", "")),
                    }

                metadata["num_pages"] = len(reader.pages)

        except Exception as e:
            self.logger.warning(f"Could not extract metadata: {e}")

        return metadata
