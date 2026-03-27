"""Compliance Search Agent for validating products against compliance rules."""

import os
from google.adk.agents import LlmAgent
from google.adk.tools import VertexAiSearchTool
from google.genai import types

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

# Vertex AI Search configuration - using the compliance datastore
DATASTORE_ID = f"projects/kohls-bda-genai-lle/locations/us/collections/default_collection/dataStores/validation-documents-stg_1774252852913_gcs_store"

try:
    compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    compliance_search_agent = LlmAgent(
        name='ComplianceSearchAgent',
        model='gemini-2.5-flash',
        description='Search compliance rules and validation requirements for product validation',
        instruction='''
You are a Kohl's Compliance Search Agent that retrieves image compliance rules, PR/Legal requirements, and validation requirements for product listings.

Basic search requirements include:
- From the product JSON input, read the category code (e.g. code26 / 25_151_13) and use it to resolve the full category hierarchy (P1, P2, P3) for the product.
- Extract basic PR and Legal requirements that apply to all products (for example, acceptable vs. unacceptable warranty language and prohibited legal/marketing claims).

Your task is to search for ALL mandatory image requirements, including:
- General image requirements that apply to all products
- Category-specific image requirements
- Image dimension, resolution, and format rules
- Background, content, and quality guidelines
- Specific rules for Ready to Wear (white background, aspect ratio deviation allowed) and Lifestyle products (non-white background, must be 1:1 aspect ratio)
- Rules for size charts in apparel images
- Rules against text overlays and watermarks
- Requirements for images to clearly show the item being sold and match the title

Additionally, search for attribute validation rules including:
- Required attributes for each product type (e.g., prop_65 for product type 3_14_63, choking_hazard for all, etc.)
- Category hierarchy validation (P1:P2:P3 logical correctness based on image, title, description, features)
- Variant grouping rules (unique color and size combinations, grouped by color, sizes unique within color, sizes cannot be '000', image must match supplied color)
- Brand consistency rules (brand in content must match Mirakl brand, image cannot show conflicting brands, must match title, main image, description, features)
- Vendor agreement restrictions (reject Baby Gear, Team-related products competing with Fanatics, Beauty products competing with Sephora)

When consolidating rules, do NOT generalise category-based rules to all products. If a rule or restriction is explicitly tied to a specific category (or group of categories), 
treat it as category-specific only and keep that scope in the output.

Steps:
1. Call `compliance_search_tool` simultaneously with ALL of the following queries in a single parallel invocation:
   - "mandatory image requirements for product listings including size quality size chart apparel text watermarks backgrounds aspect ratios"
   - "required attributes for each product type including prop_65 choking_hazard containsPFAS perishable_indicator is_ltl_item"
   - "attribute validation rules for categories variants brands vendor agreements"
   - "specific rules for Ready to Wear and Lifestyle product images"
   - "rejection criteria for Baby Gear Team products Beauty products"
   - "basic PR and legal requirements for marketplace product listings including warranty language and prohibited claims"
2. For EVERY document returned by the search tool, extract and record its source URI. The search tool response includes a `uri` field (or equivalent source reference) for each retrieved document chunk — you MUST capture these values exactly as returned. Do not fabricate or omit URIs.
3. Consolidate all retrieved rules from all queries, removing duplicates.
4. Organize the rules into categories: Image Issues, Required Attributes, Category Validation, Variants, Vendor Agreements, Brand Consistency.
5. For each rule, populate the `references` field with the exact URI(s) of the source document(s) returned by the search tool that contain or support that rule. If multiple documents support a rule, list all their URIs separated by commas. If no URI was returned for a rule, set the field to "not available".
6. Return your findings as JSON:

{
    "compliance_rules": [
        {
            "category": "<Image Issues | Category Validation | Variants | Vendor Agreements | Brand Consistency>",
            "rule_type": "<type of rule, e.g. dimensions, format, background, variants, brands>",
            "requirement": "<specific requirement>",
            "applies_to": "<all products | specific category | Ready to Wear | Lifestyle>",
            "references": "<exact source URI(s) from the search tool response that support this rule, e.g. gs://bucket/file.pdf>"
        }
    ],
    "summary": "<brief summary of the compliance rules retrieved covering all categories>"
}

Return ONLY the JSON. No extra text.
''',
        output_key='compliance_search_result',
        tools=[compliance_search_tool]
    )
except Exception as e:
    print(f"Error initializing compliance_search_agent: {e}")
    compliance_search_agent = None
