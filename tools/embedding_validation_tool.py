"""Embedding-based image validation using Vertex AI MultiModalEmbedding."""

import io
import os
import math
import tempfile
import requests
from typing import Optional, List, Dict, Any
from PIL import Image as PILImage

import vertexai
from vertexai.vision_models import Image as VertexImage
from vertexai.vision_models import MultiModalEmbeddingModel

from google.adk.tools import FunctionTool


def _pil_to_png_bytes(img: PILImage.Image) -> bytes:
    """Convert PIL Image to PNG bytes."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


def _vertex_image_from_bytes(image_bytes: bytes) -> VertexImage:
    """Create Vertex AI Image from bytes."""
    # Use delete=False on Windows due to permission issues
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        f.write(image_bytes)
        f.flush()
        f.close()  # Close before reading on Windows
        return VertexImage.load_from_file(f.name)
    finally:
        # Clean up manually
        try:
            if os.path.exists(f.name):
                os.unlink(f.name)
        except Exception:
            pass  # Best effort cleanup


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return float("nan")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return float("nan")
    return dot / (na * nb)


def _check_wrong_product_image(
    product_id: str,
    product_title: Optional[str],
    product_description: Optional[str],
    img: PILImage.Image,
    similarity_threshold: float = 0.70,
    gcp_project: Optional[str] = None,
    gcp_location: Optional[str] = None,
    embedding_model_name: str = "multimodalembedding@001",
) -> Optional[Dict[str, Any]]:
    """
    Image-to-text validation using (title + description).
    Returns an issue dict (ValidationIssue-compatible) if similarity is below threshold.
    """
    title = (product_title or "").strip()
    desc = (product_description or "").strip()
    if not title and not desc:
        return None  # no text truth to compare against

    project = gcp_project or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = (
        gcp_location
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or os.getenv("GCLOUD_LOCATION")
        or "us-central1"
    )
    if not project:
        return None  # or raise, depending on your runtime expectations

    vertexai.init(project=project, location=location)
    model = MultiModalEmbeddingModel.from_pretrained(embedding_model_name)

    # Build a concise, discriminative text blob
    text = " | ".join([s for s in [title, desc] if s])

    # Embed image
    vimg = _vertex_image_from_bytes(_pil_to_png_bytes(img))
    img_emb = model.get_embeddings(image=vimg)
    img_vec = getattr(img_emb, "image_embedding", None) or getattr(
        img_emb, "embedding", None
    )
    if not img_vec:
        return None

    # Embed text
    txt_emb = model.get_embeddings(contextual_text=text)
    txt_vec = getattr(txt_emb, "text_embedding", None) or getattr(
        txt_emb, "embedding", None
    )
    if not txt_vec:
        return None

    sim = _cosine_similarity(img_vec, txt_vec)

    if math.isnan(sim) or sim < similarity_threshold:
        return {
            "code": "INCORRECT_PRODUCT",
            "message": "Image does not appear to match the product title/description.",
            "details": {
                "product_id": product_id,
                "similarity": sim,
                "similarity_threshold": similarity_threshold,
                "method": "image_to_text_embeddings",
                "embedding_model": embedding_model_name,
                "text_used": text[:500],  # keep logs safe/short
            },
        }

    return None


def validate_image_embedding(
    products: List[Dict[str, Any]],
    similarity_threshold: float = 0.70,
    gcp_project: Optional[str] = None,
    gcp_location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate product images against their titles and descriptions using embeddings.
    
    Args:
        products: List of product dictionaries containing image URLs, titles, and descriptions.
                  Each product should have 'id' or 'mirakl_product_id', 'images', 
                  and product_attributes with 'product_title' and 'product_description'.
        similarity_threshold: Minimum cosine similarity score (0-1) for image-text match.
        gcp_project: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var).
        gcp_location: GCP region (defaults to GOOGLE_CLOUD_LOCATION env var).
    
    Returns:
        dict: Validation results with per-product results and summary
    """
    results = []
    
    # Process each product sequentially
    for product in products:
        product_id = product.get("id") or product.get("mirakl_product_id") or "unknown"
        
        # Extract image URL from product
        images = product.get("images", [])
        if not images:
            # Try alternate structure
            data = product.get("data", {})
            main_image = data.get("main_image", {})
            image_url = main_image.get("original_url") or main_image.get("source")
        else:
            image_url = images[0].get("url") if images else None
        
        if not image_url:
            results.append({
                "product_id": product_id,
                "embedding_validation": {
                    "valid": False,
                    "error": "No image URL found"
                },
            })
            continue
        
        # Extract product attributes
        product_attrs = product.get("product_attributes", {})
        product_title = product_attrs.get("product_title") or product.get("title")
        product_description = product_attrs.get("product_description") or product.get("description")
        
        if not product_title and not product_description:
            results.append({
                "product_id": product_id,
                "image_url": image_url,
                "embedding_validation": {
                    "valid": True,
                    "skipped": True,
                    "message": "No title or description to validate against"
                },
            })
            continue
        
        # Download and validate the image
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = PILImage.open(io.BytesIO(response.content))
            
            # Check for wrong product
            issue = _check_wrong_product_image(
                product_id=product_id,
                product_title=product_title,
                product_description=product_description,
                img=img,
                similarity_threshold=similarity_threshold,
                gcp_project=gcp_project,
                gcp_location=gcp_location,
            )
            
            if issue:
                validation_result = {
                    "valid": False,
                    "similarity": issue["details"]["similarity"],
                    "similarity_threshold": similarity_threshold,
                    "message": issue["message"],
                    "code": issue["code"],
                }
            else:
                validation_result = {
                    "valid": True,
                    "message": "Image matches product description",
                }
            
            results.append({
                "product_id": product_id,
                "image_url": image_url,
                "embedding_validation": validation_result,
            })
            
        except requests.exceptions.RequestException as e:
            results.append({
                "product_id": product_id,
                "image_url": image_url,
                "embedding_validation": {
                    "valid": False,
                    "error": f"Download failed: {str(e)}"
                },
            })
        except Exception as e:
            results.append({
                "product_id": product_id,
                "image_url": image_url,
                "embedding_validation": {
                    "valid": False,
                    "error": f"Validation failed: {str(e)}"
                },
            })
    
    # Calculate summary
    valid_count = sum(
        1 for r in results 
        if r.get("embedding_validation", {}).get("valid", False)
    )
    
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "valid": valid_count,
            "failed": len(results) - valid_count,
            "similarity_threshold": similarity_threshold,
        },
    }


# Create the FunctionTool
validate_image_embedding_tool = FunctionTool(func=validate_image_embedding)
