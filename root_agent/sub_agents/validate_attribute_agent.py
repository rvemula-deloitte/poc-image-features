import os
from google.adk.agents import LlmAgent
from google.adk.tools import VertexAiSearchTool
from google.genai import types


# Load environment variables
from dotenv import load_dotenv
load_dotenv()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# Vertex AI Search configuration - using direct datastore ID
# DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/poc-policy-datastore_1772199893592"

# DATASTORE_ID = f"projects/kohls-bda-genai-lle/locations/us/collections/default_collection/dataStores/validation-documents-stg_1774252852913_gcs_store"

try:
    # compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    validate_attribute_agent = LlmAgent(
        name='ValidateAttributeAgent',
        model='gemini-2.5-flash',
        description="Validate product attributes against compliance rules retrieved from Vertex AI Search",
        instruction="""
You are a Product Attribute Validation Agent.

You will receive product data from session state (products_data) and compliance rules from (compliance_search_result).

Your Task:

## STEP 1: Use Provided Compliance Rules

Use the compliance rules from {compliance_search_result} as the source of truth. Do NOT call any tools to re-fetch rules.

## STEP 2: Validate Each Product's Attributes

For every product in products_data, check:
2. **Product-Type Rules** — Do the attributes satisfy category/type-specific requirements?
3. **Data Quality** — Are values well-formed, within expected ranges, or properly formatted?
4. **Missing / Empty Fields** — List every attribute that is absent or blank.
5. **Category Validation** — Is P1:P2:P3 logically correct based on image, title, description, features?
6. **Variants** — Each variant has unique color/size, grouped by color, sizes unique within color, sizes != '000', image matches color.
7. **Brand Consistency** — Brand in content matches Mirakl brand, no conflicting brands in image/title/description/features.
8. **Vendor Agreements** — Reject if Baby Gear, Team-related (Fanatics), Beauty (Sephora).

## OUTPUT FORMAT

Return ONLY this JSON structure (no extra text):

{
  "results": [
    {
      "mirakl_product_id": "<id>",
      "product_sku": "<sku>",
      "invalid_attributes": [
        {"attribute": "<name>", "issue": "<description>"}
      ],
      "passed_checks": ["<check1>", "<check2>"],
      "failed_checks": ["<check1>", "<check2>"],
      "category_validation": {"p1_p2_p3_correct": true, "issues": []},
      "variant_validation": {"unique_combinations": true, "issues": []},
      "brand_validation": {"consistent": true, "issues": []},
      "vendor_rejection": {"rejected": false, "reason": ""},
      "ai_comments": "<detailed reasoning, point by point covering all validations>"
    }
  ],
  "summary": {
    "total_products": <number>,
    "fully_compliant": <number>,
    "partially_compliant": <number>,
    "non_compliant": <number>,
    "rejected_by_vendor": <number>
  }
}
""",
        output_key='attribute_validation_json'
    )
except Exception as e:
    print(f"Error initializing validate_attribute_agent: {e}")