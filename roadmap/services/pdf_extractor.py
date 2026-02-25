"""
PDF text extraction service for resume parsing
"""
import io
import logging
import pdfplumber
from typing import Optional, Union
from django.core.files.uploadedfile import UploadedFile

from ..utils.exceptions import PDFExtractionError, InvalidFileFormatError

# Try to import python-magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Service for extracting text content from PDF files
    """
    
    # PDF magic number signatures
    PDF_MAGIC_NUMBERS = [
        b'%PDF-',  # Standard PDF signature
    ]
    
    def __init__(self):
        """Initialize the PDF extractor"""
        self.logger = logger
    
    def extract_text(self, pdf_file: Union[UploadedFile, io.BytesIO, str]) -> str:
        """
        Extract text content from PDF file
        
        Args:
            pdf_file: PDF file to extract text from (UploadedFile, BytesIO, or file path)
            
        Returns:
            str: Extracted text content
            
        Raises:
            PDFExtractionError: If text extraction fails
            InvalidFileFormatError: If file is not a valid PDF
        """
        try:
            # Validate PDF first
            if not self.validate_pdf(pdf_file):
                raise InvalidFileFormatError("File is not a valid PDF")
            
            # Handle different file input types
            if isinstance(pdf_file, UploadedFile):
                # Reset file pointer to beginning
                pdf_file.seek(0)
                file_obj = pdf_file
            elif isinstance(pdf_file, io.BytesIO):
                file_obj = pdf_file
            elif isinstance(pdf_file, str):
                # File path
                file_obj = open(pdf_file, 'rb')
            else:
                raise PDFExtractionError(f"Unsupported file type: {type(pdf_file)}")
            
            extracted_text = ""
            
            try:
                with pdfplumber.open(file_obj) as pdf:
                    # Check if PDF has pages
                    if not pdf.pages:
                        raise PDFExtractionError("PDF file contains no pages")
                    
                    # Extract text from all pages
                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n"
                            else:
                                self.logger.warning(f"No text found on page {page_num}")
                        except Exception as e:
                            self.logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                            continue
                    
                    # Check if any text was extracted
                    if not extracted_text.strip():
                        raise PDFExtractionError("No text content could be extracted from PDF")
                    
                    self.logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
                    return extracted_text.strip()
                    
            except pdfplumber.exceptions.PDFSyntaxError as e:
                raise PDFExtractionError(f"PDF file is corrupted or malformed: {str(e)}")
            except Exception as e:
                if isinstance(e, (PDFExtractionError, InvalidFileFormatError)):
                    raise
                raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")
            
            finally:
                # Close file if we opened it
                if isinstance(pdf_file, str) and 'file_obj' in locals():
                    file_obj.close()
                    
        except Exception as e:
            if isinstance(e, (PDFExtractionError, InvalidFileFormatError)):
                raise
            raise PDFExtractionError(f"Unexpected error during PDF text extraction: {str(e)}")
    
    def validate_pdf(self, pdf_file: Union[UploadedFile, io.BytesIO, str]) -> bool:
        """
        Validate that the file is a valid PDF using magic numbers
        
        Args:
            pdf_file: File to validate
            
        Returns:
            bool: True if valid PDF, False otherwise
            
        Raises:
            InvalidFileFormatError: If file validation fails
        """
        try:
            # Handle different file input types
            if isinstance(pdf_file, UploadedFile):
                # Reset file pointer and read first few bytes
                pdf_file.seek(0)
                file_header = pdf_file.read(1024)
                pdf_file.seek(0)  # Reset for future reads
            elif isinstance(pdf_file, io.BytesIO):
                current_pos = pdf_file.tell()
                pdf_file.seek(0)
                file_header = pdf_file.read(1024)
                pdf_file.seek(current_pos)  # Restore position
            elif isinstance(pdf_file, str):
                # File path
                with open(pdf_file, 'rb') as f:
                    file_header = f.read(1024)
            else:
                raise InvalidFileFormatError(f"Unsupported file type for validation: {type(pdf_file)}")
            
            # Check magic numbers
            for magic_number in self.PDF_MAGIC_NUMBERS:
                if file_header.startswith(magic_number):
                    self.logger.debug("PDF magic number validation passed")
                    return True
            
            # Additional validation using python-magic if available
            if MAGIC_AVAILABLE:
                try:
                    if isinstance(pdf_file, UploadedFile):
                        pdf_file.seek(0)
                        file_content = pdf_file.read()
                        pdf_file.seek(0)
                    elif isinstance(pdf_file, io.BytesIO):
                        current_pos = pdf_file.tell()
                        pdf_file.seek(0)
                        file_content = pdf_file.read()
                        pdf_file.seek(current_pos)
                    elif isinstance(pdf_file, str):
                        with open(pdf_file, 'rb') as f:
                            file_content = f.read()
                    
                    mime_type = magic.from_buffer(file_content, mime=True)
                    if mime_type == 'application/pdf':
                        self.logger.debug("python-magic PDF validation passed")
                        return True
                        
                except Exception as e:
                    self.logger.warning(f"python-magic validation failed: {str(e)}")
            else:
                self.logger.debug("python-magic not available, skipping MIME type validation")
            
            self.logger.error("PDF validation failed - file does not appear to be a valid PDF")
            return False
            
        except Exception as e:
            if isinstance(e, InvalidFileFormatError):
                raise
            raise InvalidFileFormatError(f"Error validating PDF file: {str(e)}")
    
    def get_pdf_info(self, pdf_file: Union[UploadedFile, io.BytesIO, str]) -> dict:
        """
        Get basic information about the PDF file
        
        Args:
            pdf_file: PDF file to analyze
            
        Returns:
            dict: PDF information including page count, metadata, etc.
        """
        try:
            if not self.validate_pdf(pdf_file):
                raise InvalidFileFormatError("File is not a valid PDF")
            
            # Handle different file input types
            if isinstance(pdf_file, UploadedFile):
                pdf_file.seek(0)
                file_obj = pdf_file
            elif isinstance(pdf_file, io.BytesIO):
                file_obj = pdf_file
            elif isinstance(pdf_file, str):
                file_obj = open(pdf_file, 'rb')
            else:
                raise PDFExtractionError(f"Unsupported file type: {type(pdf_file)}")
            
            try:
                with pdfplumber.open(file_obj) as pdf:
                    info = {
                        'page_count': len(pdf.pages),
                        'metadata': pdf.metadata or {},
                        'has_text': False,
                        'file_size': getattr(pdf_file, 'size', None)
                    }
                    
                    # Check if PDF has extractable text
                    if pdf.pages:
                        try:
                            first_page_text = pdf.pages[0].extract_text()
                            info['has_text'] = bool(first_page_text and first_page_text.strip())
                        except Exception:
                            info['has_text'] = False
                    
                    return info
                    
            finally:
                if isinstance(pdf_file, str) and 'file_obj' in locals():
                    file_obj.close()
                    
        except Exception as e:
            if isinstance(e, (PDFExtractionError, InvalidFileFormatError)):
                raise
            raise PDFExtractionError(f"Error getting PDF info: {str(e)}")