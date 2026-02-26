from google.adk.agents import LlmAgent
from tools.tools import validate_attributes_tool



validate_attribute = LlmAgent(
    name='ValidateAttributeAgent',
    model='gemini-2.5-flash',
    description="Validate attributes for a list of products sequentially",
    instruction="""
You are an attribute validation agent.

Call the `Attribute_validation` tool with:
- products: Pass the products_data array directly

Return ONLY the JSON from the tool. No extra text.
""",
    output_key='attribute_validation_json',
    tools=[validate_attributes_tool]
)
