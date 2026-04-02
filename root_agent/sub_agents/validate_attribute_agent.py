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

try:
    # compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    validate_attribute_agent = LlmAgent(
        name='ValidateAttributeAgent',
        model='gemini-2.5-flash',
        description="Validate product attributes against compliance rules retrieved from Vertex AI Search",
        instruction="""
You are a Product Attribute Validation Agent.

You will receive product data from session state (products_data) and compliance rules from (compliance_search_result).
You must only validate attributes PR, Legal and textual data. 
Do NOT attempt to visually inspect or validate images; image compliance rules are out of scope for this agent and are handled by the ImageValidatorAgent.

Your Task:

## STEP 1: Use Provided Compliance Rules

Use the compliance rules from {compliance_search_result} as the source of truth. Do NOT call any tools to re-fetch rules.
Respect each rule's scope: if a requirement or restriction is defined as category-specific (for certain P1/P2/P3 values, product types, or groups like Ready to Wear or Lifestyle), 
apply it only to products in that category. Do not treat category-specific rules as global.

## STEP 2: Validate Each Product's Attributes

For every product in products_data, check:
2. **Product-Type Rules** — Do the attributes satisfy category/type-specific requirements? For example, if prop_65 is present, it must be "Yes" or "No"; if "No", there should be no prop_65_warning_copy provided.
3. **Data Quality** — Are values well-formed, within expected ranges, or properly formatted?
3. **Missing / Empty Fields** — From the compliance_rules where category is "Required Attributes", identify required attributes for the product's category/type. List every required attribute that is absent or blank, EXCEPT for 'prop_65' which should not be flagged as missing (only validate if present).
5. **Category Validation** — Is P1:P2:P3 logically correct based on title, description, features, and other non-image attributes?
6. **Variants** — Each variant has unique color/size, grouped by color, sizes unique within color, sizes != '000'. You may validate that the declared fields (such as color names) are logically consistent.
7. **Brand Consistency** — Brand in textual content and attributes matches Mirakl brand. Do not validate brands inside the images; that is handled by image validation.
8. **Vendor Agreements** — Reject if Baby Gear, Team-related (Fanatics), Beauty (Sephora).
9. **PR and Legal Requirements** — All products must follow Kohl's PR and Legal requirements (for example, warranty language and other legal/marketing claims must match the allowed patterns and must not use prohibited wording as defined in the compliance rules).
10. **Spelling Correctness** — Check for obvious spelling mistakes in key customer-facing fields such as title, description, bullet features, and any other textual attributes. Treat spelling issues as invalid_attributes with clear issue descriptions.

## OUTPUT FORMAT

Return ONLY this JSON structure (no extra text):

{
  "mirakl_product_id": "<id>",
  "product_sku": "<sku>",
  "invalid_attributes": [
    {"attribute": "<name>", "issue": "<description>"}
  ],
  "rule_results": [
    {"rule": "...", "passed": true, "observation": "..."}
  ],
  "category_validation": {"p1_p2_p3_correct": true, "issues": []},
  "variant_validation": {"unique_combinations": true, "issues": []},
  "brand_validation": {"consistent": true, "issues": []},
  "vendor_rejection": {"rejected": false, "reason": ""}
}
""",
        output_key='attribute_validation_json'
    )
except Exception as e:
    print(f"Error initializing validate_attribute_agent: {e}")