import requests
from io import BytesIO
from PIL import Image
from typing import Dict, Any
from google.adk.tools import FunctionTool


def get_image_dimensions(url: str) -> Dict[str, Any]:
    """
    Download an image from the given URL and return its dimensions.

    Args:
        url: The public URL of the image to inspect.

    Returns:
        dict with keys:
            - url (str): the URL that was checked
            - width (int): image width in pixels
            - height (int): image height in pixels
            - format (str): image format (e.g. JPEG, PNG)
            - error (str): present only when the image could not be fetched/opened
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        return {
            'url': url,
            'width': width,
            'height': height,
            'format': img.format or 'unknown',
        }
    except requests.exceptions.RequestException as e:
        return {'url': url, 'error': f'Download failed: {str(e)}'}
    except Exception as e:
        return {'url': url, 'error': f'Could not read image: {str(e)}'}


get_image_dimensions_tool = FunctionTool(func=get_image_dimensions)
