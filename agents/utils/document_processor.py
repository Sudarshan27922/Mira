import os
import PyPDF2
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Utility class for processing PDF documents and extracting text."""
    
    def __init__(self, docs_directory: str = "agents/docs", *, category: Optional[str] = None):
        self.docs_directory = Path(docs_directory)
        self.category = category
        if not self.docs_directory.exists():
            raise FileNotFoundError(f"Documents directory not found: {docs_directory}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from a single PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """Process all PDF documents in the docs directory."""
        documents = []
        
        # Get all PDF files
        pdf_files = list(self.docs_directory.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_file)
            
            if text:
                # Create document metadata
                doc_metadata = {
                    "source": str(pdf_file),
                    "filename": pdf_file.name,
                    "file_type": "pdf",
                    "file_size": pdf_file.stat().st_size,
                }
                if self.category:
                    doc_metadata["category"] = self.category
                
                # Split text into chunks (you can adjust chunk size as needed)
                chunks = self._split_text_into_chunks(text, chunk_size=1000, overlap=200)
                
                # Create document entries for each chunk
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "content": chunk,
                        "metadata": {
                            **doc_metadata,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    })
                
                logger.info(f"Processed {pdf_file.name}: {len(chunks)} chunks created")
            else:
                logger.warning(f"No text extracted from {pdf_file.name}")
        
        logger.info(f"Total documents processed: {len(documents)}")
        return documents
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(start + chunk_size - 100, start)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end > search_start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def get_document_summary(self) -> Dict[str, Any]:
        """Get a summary of all documents in the directory."""
        pdf_files = list(self.docs_directory.glob("*.pdf"))
        
        summary = {
            "total_files": len(pdf_files),
            "files": []
        }
        
        for pdf_file in pdf_files:
            file_info = {
                "filename": pdf_file.name,
                "size_bytes": pdf_file.stat().st_size,
                "size_mb": round(pdf_file.stat().st_size / (1024 * 1024), 2)
            }
            summary["files"].append(file_info)
        
        return summary

# Example usage
if __name__ == "__main__":
    processor = DocumentProcessor()
    
    # Get document summary
    summary = processor.get_document_summary()
    print(f"Found {summary['total_files']} PDF files:")
    for file_info in summary["files"]:
        print(f"  - {file_info['filename']} ({file_info['size_mb']} MB)")
    
    # Process documents
    print("\nProcessing documents...")
    documents = processor.process_all_documents()
    print(f"Created {len(documents)} document chunks")
