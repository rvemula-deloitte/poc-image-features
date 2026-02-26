from google.adk.agents import LlmAgent
from tools.tools import validate_image_tool



validate_image_agent = LlmAgent(
    name='ImageValidatorAgent',
    model='gemini-2.5-flash',
    description='Validate images for a list of products sequentially',
    instruction='''
You are an image validation agent.

Call the `validate_image` tool with:
- products: Pass the products_data array directly

Return ONLY the JSON from the tool. No extra text.
''',
    output_key='image_validation_json',
    tools=[validate_image_tool]
)
