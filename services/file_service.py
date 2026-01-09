import logging
import io
import requests
from bs4 import BeautifulSoup
from docx import Document

logger = logging.getLogger(__name__)

async def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extracts text from DOCX or TXT files.
    """
    try:
        ext = filename.split('.')[-1].lower()
        
        if ext == 'txt':
            return file_content.decode('utf-8')
            
        elif ext == 'docx':
            doc = Document(io.BytesIO(file_content))
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
            
        else:
            return ""
            
    except Exception as e:
        logger.error(f"Error extracting text from {filename}: {e}")
        return ""

async def scrape_url(url: str) -> str:
    """
    Fetches and extracts text from a URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Kill all script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:10000] # Limit to 10k chars to avoid blowing up context
        
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}")
        return f"Error scraping URL: {str(e)}"
