import json
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from ..tools.tools import get_image_dimensions_tool


def _detect_mime(url: str) -> str:
    """Infer MIME type from image URL extension."""
    lower = url.lower().split("?")[0]
    if lower.endswith(".png"):  return "image/png"
    if lower.endswith(".webp"): return "image/webp"
    if lower.endswith(".gif"):  return "image/gif"
    return "image/jpeg"


def _extract_image_url(img_obj: dict) -> Optional[str]:
    """Return the best available URL from a Mirakl image object."""
    if not isinstance(img_obj, dict):
        return None
    # Prefer original_url (source CDN); fall back to mirakl-hosted source
    return img_obj.get("original_url") or img_obj.get("source") or None


def _inject_product_images(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """
    Before-model callback: reads all product image URLs from session state
    and injects them as Part.from_uri directly into the Gemini request.

    Handles Mirakl product JSON structure:
      - product["mirakl_product_id"]  → product ID
      - product["data"]["main_image"] → main image  {original_url, source}
      - product["data"]["alt_image_1"],
        product["data"]["alt_image_2"], ... (any number) → alternate images

    Each image is preceded by a descriptive text label so the agent can
    reference it by product ID and image type.
    """
    state = callback_context.state
    raw = state.get("products_data", "[]")
    try:
        products = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(products, list):
            products = [products] if isinstance(products, dict) else []
    except Exception:
        products = []

    image_parts: list[genai_types.Part] = []

    for product in products:
        product_id = (
            product.get("mirakl_product_id")
            or product.get("id")
            or "unknown"
        )
        data = product.get("data") or {}

        # ── Main image ──────────────────────────────────────────────────────
        main_url = _extract_image_url(data.get("main_image") or {})
        if main_url:
            image_parts.append(genai_types.Part(
                text=f"[Product ID: {product_id} | image_type: main | url: {main_url}]"
            ))
            image_parts.append(
                genai_types.Part.from_uri(file_uri=main_url, mime_type=_detect_mime(main_url))
            )

        # ── Alternate images: alt_image_1, alt_image_2, … (any count) ──────
        for key in (k for k in data if k.startswith("alt_image_")):
            alt_url = _extract_image_url(data.get(key) or {})
            if not alt_url:
                continue
            image_parts.append(genai_types.Part(
                text=f"[Product ID: {product_id} | image_type: alternate ({key}) | url: {alt_url}]"
            ))
            image_parts.append(
                genai_types.Part.from_uri(file_uri=alt_url, mime_type=_detect_mime(alt_url))
            )

    if image_parts:
        llm_request.contents.append(
            genai_types.Content(role="user", parts=image_parts)
        )

    return None  # continue with the (now enriched) request


validate_image_agent = LlmAgent(
    name='ImageValidatorAgent',
    model='gemini-2.5-flash',
    description='Validate all product images (main + alternate) directly via Gemini vision using Part.from_uri',
    before_model_callback=_inject_product_images,
    instruction='''
You are an image validation agent.

The product images have been injected directly into this conversation as inline image parts.
Each image is preceded by a text label: [Product ID: <id> | image_type: main|alternate | url: <url>]

## STEP 1 — Compliance Rules (already in state)
Use the compliance rules exactly as provided — do NOT call any tool to re-fetch them.

{compliance_search_result}

## STEP 2 — Dimensions
For every image URL labelled above, call `get_image_dimensions_tool` with that URL
to get exact pixel width, height, and format.

## STEP 3 — Visual Compliance Check
For each injected image, visually inspect it against every compliance rule from Step 1, including:
- Image size and quality (resolution, clarity, no blur)
- Size chart inclusion for apparel
- Clearly shows the item being sold
- Correct item compared to title
- No text overlays or watermarks
- Background rules: Ready to Wear must have white background (some deviation from 1:1 aspect ratio allowed); Lifestyle can have non-white background but must be 1:1 aspect ratio
- Brand consistency in images (no conflicting brands)
- For variants: image logically matches supplied color

## STEP 4 — Return aggregated results

Return ONLY valid JSON. No extra text. Format:
{
    "results": [
        {
            "product_id": "...",
            "image_url": "...",
            "image_type": "main",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "compliant": true,
            "compliance_score": 92,
            "rule_results": [
                {"rule": "...", "passed": true, "observation": "..."}
            ],
            "issues": [],
            "details": "..."
        }
    ],
    "summary": {
        "total": 3,
        "compliant": 2,
        "non_compliant": 1
    },
    "compliance_rules_applied": ["..."]
}
''',
    output_key='image_validation_json',
    tools=[get_image_dimensions_tool],
)
