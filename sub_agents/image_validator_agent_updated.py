"""
Image Validation Agent (Google ADK + Gemini)

What it does:
- Validates main + alternate images by URL
- OCR + prohibited text detection (e.g., "warranty", "lifetime guarantee")
- Main image: reject if cluttered OR shows same product more than once
- Alt images: flag spelling issues and "accuracy" issues via LLM
- Furniture: require explicit dimensions on an alt image for every color variant
- LLM: verify each image matches listing title + description

Notes:
- This is a practical template. Wire it into your ADK runner / deployment.
- Gemini can OCR and interpret images (multimodal), so we rely on LLM OCR here.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal, Tuple

import aiohttp
from pydantic import BaseModel, HttpUrl, Field

from google import genai
from google.genai.types import Part, HttpOptions


# -----------------------------
# Policy config
# -----------------------------
BANNED_PATTERNS = [
    r"\bwarranty\b",
    r"\blifetime\s+guarantee\b",
]
BANNED_RE = re.compile("|".join(BANNED_PATTERNS), flags=re.IGNORECASE)

# Dimension patterns (broad; tune to your marketplace)
DIMENSION_RE = re.compile(
    r"(\bW\b.*\bD\b.*\bH\b)|"
    r"(\b\d+(\.\d+)?\s?(in|inch|\"|cm|mm)\b.*[x×]\s*\d)|"
    r"(\b\d+(\.\d+)?\s*[x×]\s*\d+(\.\d+)?\s*[x×]\s*\d+(\.\d+)?\b)",
    flags=re.IGNORECASE,
)

MAX_BYTES = 8 * 1024 * 1024
TIMEOUT_S = 20


# -----------------------------
# Input / Output models
# -----------------------------
class ListingInput(BaseModel):
    title: str
    description: str
    product_category: Optional[str] = None  # e.g., "furniture"
    color_variants: Optional[List[str]] = None  # e.g., ["black", "white"]
    main_image_url: HttpUrl
    alt_image_urls: List[HttpUrl] = Field(default_factory=list)


class ImageFinding(BaseModel):
    url: HttpUrl
    role: Literal["main", "alt"]
    ocr_text: str = ""
    prohibited_hits: List[str] = Field(default_factory=list)
    has_dimensions: bool = False
    cluttered: Optional[bool] = None
    duplicate_product_in_frame: Optional[bool] = None
    matches_title_description: Optional[bool] = None
    match_rationale: Optional[str] = None
    spelling_suspects: List[str] = Field(default_factory=list)
    accuracy_flags: List[str] = Field(default_factory=list)
    llm_confidence: Optional[float] = None  # 0..1


class ValidationReport(BaseModel):
    overall: Literal["pass", "reject"]
    rejection_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    main: ImageFinding
    alts: List[ImageFinding] = Field(default_factory=list)
    furniture: Optional[Dict[str, Any]] = None


# -----------------------------
# Utility: URL fetch + basic validation
# -----------------------------
async def fetch_image_bytes(url: str) -> Tuple[bytes, str]:
    """
    Downloads an image (with size cap) and returns (bytes, content_type).
    Use this to validate URL accessibility + content-type before LLM calls.
    """
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_S)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            total = 0
            chunks = []
            async for chunk in resp.content.iter_chunked(64 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError(f"Image too large (> {MAX_BYTES} bytes): {url}")
                chunks.append(chunk)
            return b"".join(chunks), ctype


def banned_hits(text: str) -> List[str]:
    hits = []
    for m in BANNED_RE.finditer(text or ""):
        hits.append(m.group(0))
    # de-dup preserve order
    out, seen = [], set()
    for h in hits:
        k = h.lower()
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def has_dimensions(text: str) -> bool:
    return bool(DIMENSION_RE.search(text or ""))


def spelling_suspects_simple(text: str) -> List[str]:
    """
    Lightweight spell suspecting without a dictionary (safe default).
    Flags: long alphabetic tokens with weird consonant runs or repeated chars.
    Replace with Hunspell + allowlist in production.
    """
    tokens = re.findall(r"[A-Za-z]{5,}", text or "")
    suspects = []
    for t in tokens:
        tl = t.lower()
        if re.search(r"(.)\1\1", tl):  # e.g., "greeeeat"
            suspects.append(t)
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", tl):  # long consonant run
            suspects.append(t)
    out, seen = [], set()
    for s in suspects:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


# -----------------------------
# LLM tool: analyze image w/ Gemini (OCR + semantics)
# -----------------------------
GEMINI_MODEL = "gemini-1.5-flash"  # choose per your latency/quality needs

def gemini_client() -> genai.Client:
    # Auth: set GOOGLE_API_KEY (AI Studio) or use Vertex AI ADC in your runtime.
    return genai.Client(http_options=HttpOptions(api_version="v1"))


async def gemini_analyze_image(
    url: str,
    role: Literal["main", "alt"],
    title: str,
    description: str,
    product_category: Optional[str] = None,
    color_variants: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Uses Gemini multimodal OCR + reasoning to produce structured findings.
    """
    prompt = {
        "task": "image_listing_validation",
        "inputs": {
            "role": role,
            "listing_title": title,
            "listing_description": description,
            "product_category": product_category,
            "color_variants": color_variants,
            "image_url": url,
        },
        "rules": {
            "main_image": "Reject if cluttered OR shows exact same product more than once in primary photo.",
            "alt_images": "Review for spelling errors and accuracy.",
            "prohibited_text": "Reject if image contains words like 'warranty' or 'lifetime guarantee'.",
            "furniture": "If furniture, dimensions must be explicitly shown on an alt image for every color variant.",
            "match_check": "Verify image content matches title+description; flag mismatches.",
        },
        "output_schema": {
            "ocr_text_verbatim": "string",
            "cluttered": "boolean|null",
            "duplicate_product_in_frame": "boolean|null",
            "matches_title_description": "boolean|null",
            "match_rationale": "string|null",
            "accuracy_flags": ["string"],
            "confidence_0_to_1": "number"
        },
        "instructions": [
            "Extract ALL visible text exactly as seen (ocr_text_verbatim).",
            "If unsure, set boolean fields to null and explain in match_rationale.",
            "Return STRICT JSON only, no markdown."
        ],
    }

    client = gemini_client()
    # Use URL directly (Gemini Part.from_uri supports URI inputs).
    # For best reliability in production, prefer GCS URLs.
    contents = [
        json.dumps(prompt),
        Part.from_uri(file_uri=url, mime_type="image/*"),
    ]

    # google-genai client is sync; run in thread to keep async interface
    loop = asyncio.get_running_loop()
    def _call():
        model = client.models.get(GEMINI_MODEL)
        resp = model.generate_content(contents=contents)
        return (resp.text or "").strip()

    raw = await loop.run_in_executor(None, _call)

    # Parse JSON robustly (strip accidental leading/trailing text)
    try:
        # best-effort extraction of first JSON object
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start:end+1])
    except Exception as e:
        raise ValueError(f"Gemini JSON parse failed: {e}; raw={raw[:400]}")

    return data


# -----------------------------
# Policy engine (deterministic)
# -----------------------------
def apply_policy(
    main: ImageFinding,
    alts: List[ImageFinding],
    product_category: Optional[str],
    color_variants: Optional[List[str]],
) -> Tuple[Literal["pass", "reject"], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    reasons: List[Dict[str, Any]] = []

    # Prohibited verbiage anywhere => reject
    banned_any = []
    if main.prohibited_hits:
        banned_any.append({"url": str(main.url), "hits": main.prohibited_hits})
    for a in alts:
        if a.prohibited_hits:
            banned_any.append({"url": str(a.url), "hits": a.prohibited_hits})
    if banned_any:
        reasons.append({"rule": "prohibited_verbiage", "detail": banned_any})

    # Main image: cluttered or duplicate product => reject
    if main.cluttered is True:
        reasons.append({"rule": "main_image_cluttered", "detail": {"url": str(main.url)}})
    if main.duplicate_product_in_frame is True:
        reasons.append({"rule": "main_image_duplicate_product", "detail": {"url": str(main.url)}})

    # Main image must match title/description => reject (tuneable)
    if main.matches_title_description is False:
        reasons.append({
            "rule": "main_image_mismatch_title_description",
            "detail": {"url": str(main.url), "rationale": main.match_rationale}
        })

    # Alt images: spelling/accuracy (default: flag but do not hard-reject)
    # If you want strict mode, convert flags into rejection reasons.
    # Example strict toggle:
    STRICT_ALT_TEXT = False
    if STRICT_ALT_TEXT:
        bad_alts = []
        for a in alts:
            if a.spelling_suspects or a.accuracy_flags:
                bad_alts.append({
                    "url": str(a.url),
                    "spelling_suspects": a.spelling_suspects,
                    "accuracy_flags": a.accuracy_flags,
                })
        if bad_alts:
            reasons.append({"rule": "alt_images_text_accuracy", "detail": bad_alts})

    # Furniture: dimensions per color variant
    furniture_detail = None
    if (product_category or "").lower() == "furniture":
        dim_alts = [a for a in alts if a.has_dimensions]
        if color_variants:
            coverage = {v: [] for v in color_variants}
            unmapped = []
            for a in dim_alts:
                u = str(a.url).lower()
                mapped = None
                for v in color_variants:
                    if v.lower() in u:
                        mapped = v
                        break
                if mapped:
                    coverage[mapped].append(str(a.url))
                else:
                    unmapped.append(str(a.url))

            missing = [v for v, urls in coverage.items() if not urls]
            furniture_detail = {
                "dimension_alt_images": [str(a.url) for a in dim_alts],
                "variant_coverage": coverage,
                "unmapped_dimension_images": unmapped,
                "missing_variants": missing,
            }
            if missing:
                reasons.append({"rule": "furniture_dimensions_per_variant_missing", "detail": furniture_detail})
        else:
            furniture_detail = {
                "dimension_alt_images": [str(a.url) for a in dim_alts],
                "note": "Provide color_variants to enforce per-variant requirement.",
            }
            if not dim_alts:
                reasons.append({"rule": "furniture_dimensions_missing", "detail": furniture_detail})

    overall: Literal["pass", "reject"] = "reject" if reasons else "pass"
    return overall, reasons, furniture_detail


# -----------------------------
# ADK agent wiring (template)
# -----------------------------
"""
ADK concepts used:
- Agent configured with instructions + model + tools [^6^](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFQkS-Apws4gzDU7qiIpLEy1P-XC8kJha-CwhVa_2A-L81EixOaj6BAdBwhWjH2stC5qsa67KWL2ggIA5z3iw6EYjOCLLHVYnEJCR1TYOD7-TQLmj7jHDuoCJEo6V8DuUMluQKZKvcymSBn2nsWWhOp4XPznA==)
- Tools defined as Python functions; schema inferred from signature/docstring [^8^](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGbQ4GCfzM_jnB23qC6DyyGwk2koxMOxTCF1WPyrfiWUA0C5VnC6qLzY6WLcE-BunQb-J_Np_CLkZy3Q0KvH_ZnfGgk8eGWcLZqWMsNKe4-PRANW1iPm9c3wUrVYPjTuLR5mfI0FWaEHounaVVQevARhtyLMxb6EQY=)
- Orchestration patterns like SequentialAgent / routing are supported [^3^](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQGBSYxA1vAzKvVErIRDAHDwNTKdx82TG7nwcB58UYWDlMmHFIOrdt5xGc9HYs4Td_B0sX5SrYq1hQtvNj1TbE0hUCCIVXbITKA6-4NDnakoKJPBtffdVoEsthq7Ag==) [^10^](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQE6jTfT7ls4OEBUBCVu9Hlh2E1ESoBrO4DM44o98OailtBunwqhUC4-jRCM1TeQhSrc1Czr_2PZWwTj18uol7EHS2AZHJf0Dku31Mwv9T4FEa5xlT9ibhdqK4THTyamyBar451FN071xaISt-rMAuhQ9Mic1X__uT4-3QipFq8aGmulwcA39EQlv_TIsF91_cfX7JoX6Gv5hLj6VWddHw0RW_HXQoc6sC--lJB4POoh)

Replace the placeholder imports/classes below with your ADK package’s actual names
(e.g., your org’s pinned ADK version).
"""

# --- PLACEHOLDER ADK API (adapt to your ADK version) ---
class ADKAgent:
    def __init__(self, name: str, instructions: str, tools: list):
        self.name = name
        self.instructions = instructions
        self.tools = tools

class ADKRunner:
    def __init__(self, agent: ADKAgent):
        self.agent = agent

    async def run(self, user_input: dict) -> dict:
        # In real ADK, the runner drives tool-calling with the model.
        # Here we call deterministically for an MVP.
        return await validate_listing(user_input)


# -----------------------------
# Agent "tool": validate listing (deterministic orchestration)
# -----------------------------
async def validate_listing(payload: dict) -> dict:
    """
    Tool: Validates a listing's main + alt images against policy.
    Input: ListingInput-compatible dict.
    Output: ValidationReport dict.
    """
    inp = ListingInput(**payload)

    # (Optional) preflight: ensure URLs are reachable + are images
    # In production, also enforce domain allowlist and prefer GCS URLs.
    urls = [str(inp.main_image_url)] + [str(u) for u in inp.alt_image_urls]
    preflight: Dict[str, Dict[str, Any]] = {}
    async def _pre(u: str):
        try:
            b, ctype = await fetch_image_bytes(u)
            preflight[u] = {"ok": True, "content_type": ctype, "bytes": len(b)}
        except Exception as e:
            preflight[u] = {"ok": False, "error": str(e)}

    await asyncio.gather(*[_pre(u) for u in urls])
    bad = [u for u, r in preflight.items() if not r.get("ok")]
    if bad:
        raise ValueError(f"Image URL preflight failed: {bad}")

    # Analyze main + alts with Gemini (multimodal OCR + reasoning)
    main_llm = await gemini_analyze_image(
        url=str(inp.main_image_url),
        role="main",
        title=inp.title,
        description=inp.description,
        product_category=inp.product_category,
        color_variants=inp.color_variants,
    )
    alt_llm_list = await asyncio.gather(*[
        gemini_analyze_image(
            url=str(u),
            role="alt",
            title=inp.title,
            description=inp.description,
            product_category=inp.product_category,
            color_variants=inp.color_variants,
        )
        for u in inp.alt_image_urls
    ])

    # Convert to findings + deterministic enrichments
    main = ImageFinding(
        url=inp.main_image_url,
        role="main",
        ocr_text=main_llm.get("ocr_text_verbatim", "") or "",
        prohibited_hits=banned_hits(main_llm.get("ocr_text_verbatim", "") or ""),
        has_dimensions=has_dimensions(main_llm.get("ocr_text_verbatim", "") or ""),
        cluttered=main_llm.get("cluttered"),
        duplicate_product_in_frame=main_llm.get("duplicate_product_in_frame"),
        matches_title_description=main_llm.get("matches_title_description"),
        match_rationale=main_llm.get("match_rationale"),
        accuracy_flags=list(main_llm.get("accuracy_flags") or []),
        llm_confidence=float(main_llm.get("confidence_0_to_1") or 0.0),
    )
    main.spelling_suspects = spelling_suspects_simple(main.ocr_text)

    alts: List[ImageFinding] = []
    for u, llm in zip(inp.alt_image_urls, alt_llm_list):
        ocr = llm.get("ocr_text_verbatim", "") or ""
        a = ImageFinding(
            url=u,
            role="alt",
            ocr_text=ocr,
            prohibited_hits=banned_hits(ocr),
            has_dimensions=has_dimensions(ocr),
            matches_title_description=llm.get("matches_title_description"),
            match_rationale=llm.get("match_rationale"),
            accuracy_flags=list(llm.get("accuracy_flags") or []),
            llm_confidence=float(llm.get("confidence_0_to_1") or 0.0),
        )
        a.spelling_suspects = spelling_suspects_simple(ocr)
        alts.append(a)

    overall, reasons, furniture_detail = apply_policy(main, alts, inp.product_category, inp.color_variants)

    report = ValidationReport(
        overall=overall,
        rejection_reasons=reasons,
        main=main,
        alts=alts,
        furniture=furniture_detail,
    )
    return report.model_dump()


# -----------------------------
# Build the ADK agent
# -----------------------------
def build_agent() -> Tuple[ADKAgent, ADKRunner]:
    instructions = """
You are an Image Validation Agent.
Given listing title, description, main image URL, and alt image URLs:
- Enforce prohibited verbiage rejection.
- Enforce main image: not cluttered; not repeated product in frame; matches title/description.
- Enforce furniture: dimensions per color variant in alt images.
- Produce a structured pass/reject report with reasons.
"""
    # In real ADK, you'd register the tool functions (validate_listing, etc.)
    agent = ADKAgent(
        name="image_validation_agent",
        instructions=instructions,
        tools=[validate_listing],  # plus individual tools if you want LLM-driven orchestration
    )
    runner = ADKRunner(agent)
    return agent, runner


# -----------------------------
# Local test harness
# -----------------------------
async def _demo():
    _, runner = build_agent()
    payload = {
        "title": "Modern Oak Coffee Table, 42 inch",
        "description": "Solid oak coffee table with matte finish. Includes dimensions in inches.",
        "product_category": "furniture",
        "color_variants": ["oak", "walnut"],
        "main_image_url": "https://YOUR_PUBLIC_OR_GCS_URL/main.jpg",
        "alt_image_urls": [
            "https://YOUR_PUBLIC_OR_GCS_URL/alt_oak_dims.jpg",
            "https://YOUR_PUBLIC_OR_GCS_URL/alt_walnut_dims.jpg",
        ],
    }
    result = await runner.run(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_demo())

