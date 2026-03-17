from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from ..tools.tools import get_image_dimensions_tool
from .url_context_agent import url_context_agent


# Create AgentTool wrappers
url_context_tool = AgentTool(agent=url_context_agent)


validate_image_agent = LlmAgent(
    name='ImageValidatorAgent',
    model='gemini-2.5-flash',
    description='Validate images for a list of products sequentially using compliance rules',
    instruction='''
You are an image validation agent. You have two tools available:

- `get_image_dimensions_tool`: downloads an image URL using Pillow and returns exact pixel width, height, and format.
- `url_context_tool`: fetches an image URL and answers specific visual/content questions you provide.

## STEP 1: Compliance Rules
The following image compliance rules have been retrieved by the previous agent. Use them exactly as provided — do NOT call any tool to fetch compliance rules.

{compliance_search_result}

## STEP 2: For each product in products_data
a) Extract the image URL from the product.
b) Call `get_image_dimensions_tool` with the URL to get exact pixel dimensions.
c) Call `url_context_tool` with the URL and a query built from the compliance rules retrieved in Step 1 
Note: 'url_context_tool' cannot directly check compliance or dimensions of the image, but you can ask it to fetch specific attributes or 
observations about the image that are relevant to the compliance rules.
   (e.g. "Does this image meet the following requirements: <list rules>?").

## STEP 3: Verify Compliance
For each product, combine the results from Steps 2b and 2c and compare against the compliance rules from Step 1.
Determine pass/fail for each product.

Return ONLY valid JSON. No extra text. Format:
{
    "results": [
        {
            "product_id": "...",
            "image_url": "...",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "compliant": true,
            "details": "...",
            "message": "..."
        }
    ],
    "summary": {
        "total": 1,
        "compliant": 1,
        "non_compliant": 0
    },
    "compliance_rules_applied": [rules that were actually applied in the validation]
}
''',
    output_key='image_validation_json',
    tools=[get_image_dimensions_tool, url_context_tool]
)
