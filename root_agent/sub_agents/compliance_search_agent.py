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
DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/validation-documents-stg_1774252852913_gcs_store"

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
1. Call `compliance_search_tool` simultaneously with ALL of the following queries in a single parallel invocation:
   - "mandatory image requirements for product listings"
   - "image validation rules dimensions format background"
2. Consolidate all retrieved rules from all queries, removing duplicates.
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
