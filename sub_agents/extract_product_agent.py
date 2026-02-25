from google.adk.agents import LlmAgent
from tools.tools import fetch_product_from_api


extract_product = LlmAgent(
    name = 'ExtractProductAgent',
    model ='gemini-2.5-flash',
    instruction='''
Call fetch_product_from_api with the product ID (1-30).

CRITICAL: Return ONLY the exact JSON object from the tool.
Do NOT add any text, explanation, or formatting.
Your entire response must be valid JSON.

Example output:
{"id": "1", "product_type": "beauty", "product_attributes": {...}, "images": [...]}
''',
tools=[fetch_product_from_api],
output_key='prodcut_details'
)
