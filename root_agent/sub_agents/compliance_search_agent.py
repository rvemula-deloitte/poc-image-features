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
# DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/poc-policy-datastore_1772199893592"

DATASTORE_ID = f"projects/kohls-bda-genai-lle/locations/us/collections/default_collection/dataStores/validation-documents-stg_1774252852913_gcs_store"



try:
    compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    compliance_search_agent = LlmAgent(
        name='ComplianceSearchAgent',
        model='gemini-2.5-flash',
        description='Search compliance rules and validation requirements for product validation',
        instruction='''
You are a Compliance Search Agent that retrieves image compliance rules and validation requirements for product listings.

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
- Category hierarchy validation (P1:P2:P3 logical correctness based on image, title, description, features)
- Variant grouping rules (unique color and size combinations, grouped by color, sizes unique within color, sizes cannot be '000', image must match supplied color)
- Brand consistency rules (brand in content must match Mirakl brand, image cannot show conflicting brands, must match title, main image, description, features)
- Vendor agreement restrictions (reject Baby Gear, Team-related products competing with Fanatics, Beauty products competing with Sephora)

Steps:
1. Call `compliance_search_tool` simultaneously with ALL of the following queries in a single parallel invocation:
   - "mandatory image requirements for product listings including size quality size chart apparel text watermarks backgrounds aspect ratios"
   - "attribute validation rules for categories variants brands vendor agreements"
   - "specific rules for Ready to Wear and Lifestyle product images"
   - "rejection criteria for Baby Gear Team products Beauty products"
2. Consolidate all retrieved rules from all queries, removing duplicates.
3. Organize the rules into categories: Image Issues, Category Validation, Variants, Vendor Agreements, Brand Consistency.
4. Return your findings as JSON:

{
    "compliance_rules": [
        {
            "category": "<Image Issues | Category Validation | Variants | Vendor Agreements | Brand Consistency>",
            "rule_type": "<type of rule, e.g. dimensions, format, background, variants, brands>",
            "requirement": "<specific requirement>",
            "applies_to": "<all products | specific category | Ready to Wear | Lifestyle>",
            "references": "<relevant chunks or sources from datastore>"
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
