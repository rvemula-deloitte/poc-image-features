from google.adk.agents import LlmAgent
from tools.tools import Attribute_validation



validate_attribute = LlmAgent(
    name='ValidateAttributeAgent',
    model='gemini-2.5-flash',
    description="validate the attribute of product",
    instruction="""
Extract product_type and product_attributes from {prodcut_details} and call Attribute_validation tool.

CRITICAL: Return ONLY the exact JSON object from the tool.
Do NOT add any text, explanation, or formatting.
Your entire response must be valid JSON.

Example output:
{"status": "success", "valid": true, "message": "...", "missing_attributes": [], "empty_attributes": [], "required_attributes": [...], "provided_attributes": [...]}
""",
tools=[Attribute_validation],
output_key = 'attribute_validation_json'
)
