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
DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/poc-policy-datastore_1772199893592"

try:
    compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    compliance_search_agent = LlmAgent(
        name='ComplianceSearchAgent',
        model='gemini-2.5-flash',
        description='Search compliance rules and validation requirements for product validation',
        instruction='''
You are a Compliance Search Agent that retrieves compliance rules and validation requirements.

You will receive a specific query from the calling agent. Your job is to search ONLY for what was asked — do NOT retrieve unrelated compliance topics.

Steps:
1. Read the query provided to you carefully.
2. Use the Vertex AI Search tool with that exact query to retrieve relevant compliance rules.
3. Extract only the rules that directly answer the query — discard unrelated results.
4. Return your findings as JSON:

{
    "query": "<the search query you received>",
    "compliance_rules": [
        {
            "rule_type": "<type of rule>",
            "requirement": "<specific requirement>",
            "applies_to": "<what products this applies to>"
        }
    ],
    "summary": "<brief summary of only the rules relevant to the query>"
}

Important: Do NOT search for topics that were not asked. Only return compliance rules that are directly relevant to the received query.
''',
        output_key='compliance_search_result',
        tools=[compliance_search_tool],
        generate_content_config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=10,
            ),
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="AUTO",
                    allowed_function_names=[compliance_search_tool.name]
                )
            )
        ),
    )
except Exception as e:
    print(f"Error initializing compliance_search_agent: {e}")
    compliance_search_agent = None
