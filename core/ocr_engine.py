import pytesseract
from PIL import Image
import os

# Configure Tesseract path centrally
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text from the image
    """
    try:
        if not os.path.exists(image_path):
            return "Error: Image file not found."
            
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"
