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
DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/kohls-drive-connector_1773743180176/dataStores/kohls-drive-connector_1773743180176_google_drive"

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

Steps:
1. Use the Vertex AI Search tool with the query: "mandatory image requirements for product listings"
2. Also search for: "image validation rules dimensions format background"
3. Consolidate all retrieved rules, removing duplicates.
4. Return your findings as JSON:

{
    "compliance_rules": [
        {
            "rule_type": "<type of rule, e.g. dimensions, format, background>",
            "requirement": "<specific requirement>",
            "applies_to": "<all products | specific category>"
        }
    ],
    "summary": "<brief summary of the image compliance rules retrieved>"
}

Return ONLY the JSON. No extra text.
''',
        output_key='compliance_search_result',
        tools=[compliance_search_tool]
    )
except Exception as e:
    print(f"Error initializing compliance_search_agent: {e}")
    compliance_search_agent = None
