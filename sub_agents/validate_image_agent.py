from google.adk.agents import LlmAgent
from tools.tools import validate_image



validate_image_agent = LlmAgent(
    name='ImageValidatorAgent',
    model='gemini-2.5-flash',
    description='Validate image using tool to check their diamentions',
    instruction='''
Extract image URL from {prodcut_details} and call validate_image tool.

CRITICAL: Return ONLY the exact JSON object from the tool.
Do NOT add any text, explanation, or formatting.
Your entire response must be valid JSON.

Example output:
{"valid": false, "width": 1000, "height": 1000, "min_required": "1920×1080", "actual": "1000×1000", "message": "..."}
''',
output_key = 'image_validation_json',
tools=[validate_image]
)
