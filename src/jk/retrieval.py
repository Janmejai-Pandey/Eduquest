import os
import re
import pdfplumber

def initialize_pdf_retrieval(pdf_path):
    """Loads and extracts text content per page for indexing."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Target PDF not found at: {pdf_path}")
        
    document_index = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                # Store text along with metadata for precise retrieval mapping
                document_index.append({
                    "page_number": index + 1,
                    "content": text
                })
    return document_index

def retrieve_by_keyword(document_index, keyword):
    """Retrieves sentences containing a specific keyword (Boolean/Keyword Search)."""
    results = []
    # Compile safe case-insensitive exact word matching
    pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    
    for page in document_index:
        # Split text into sentences for granular retrieval
        sentences = re.split(r'(? {hit['entity']}")
            
    except FileNotFoundError as e:
        print(e)
