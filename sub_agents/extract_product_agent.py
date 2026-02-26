from google.adk.agents import LlmAgent
from tools.tools import fetch_products_tool


extract_product = LlmAgent(
    name = 'ExtractProductAgent',
    model ='gemini-2.5-flash',
    instruction='''
Call fetch_products_from_mirakl to retrieve product data from the Mirakl API.

Parameters you can use:
- updated_since: ISO 8601 date string (e.g., "2026-02-15T09:31:48Z")
- updated_to: ISO 8601 date string (e.g., "2026-02-23T16:51:48Z")  
- product_sku: Optional SKU filter (e.g., "4135850671899")

CRITICAL: Return ONLY the exact JSON array from the tool.
Do NOT add any text, explanation, or formatting.
Your entire response must be valid JSON.
''',
tools=[fetch_products_tool],
output_key='products_data'
)
