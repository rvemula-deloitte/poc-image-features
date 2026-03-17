import os
from google.adk.agents import LlmAgent
from google.adk.tools import VertexAiSearchTool
from google.genai import types


# Load environment variables
from dotenv import load_dotenv
load_dotenv()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# Vertex AI Search configuration - using direct datastore ID
DATASTORE_ID = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/poc-policy-datastore_1772199893592"

try:
    compliance_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

    validate_and_score_agent = LlmAgent(
        name='ValidateAndScoreAgent',
        model='gemini-2.5-flash',
        description="Validate attributes and calculate confidence score using compliance rules from Vertex AI Search",
        instruction="""
    You are a Product Validation and Reliability Scoring Agent.

    You will receive:
    1. Product data to validate
    2. Image validation results: {image_validation_json}

    Your Task:

    ## STEP 1: Retrieve Compliance Rules

    Use the Vertex AI Search tool to look up:
    - Required attributes for all products (search: "common required attributes")
    - Product-type specific required attributes (search: "required attributes for product type <product_type>")
    - Image validation requirements (search: "image validation requirements")

    ## STEP 2: Validate and Score

    Analyze each product and determine its reliability based on:

    1. **Compliance Rules** (from search results)
    - Required attributes for all products
    - Product-type specific required attributes
    - Validation rules

    2. **Image Validation Results**
    - Whether the product image meets requirements

    3. **Product Data Quality**
    - Completeness of attributes
    - Missing or empty required fields
    - Overall data integrity

    Based on your analysis of all these factors, provide:
    - A confidence score (0-100) representing how reliable/compliant the product is
    - A confidence level (High/Good/Medium/Low)
    - Reasoning for your assessment
    - List of issues found

    ## OUTPUT FORMAT

    Return ONLY this JSON structure (no extra text):

    {
    "results": [
        {
        "mirakl_product_id": "<id>",
        "product_sku": "<id>",
        "confidence_score": <0-100>,
        "ai_comments": "<reasoning and issues found. mention specific missing attributes, image validation failures, and any other compliance issues point by point.>",
        }
    ],
    "summary": {
        "total_products": <number>,
        "high_confidence": <number>,
        "good_confidence": <number>,
        "medium_confidence": <number>,
        "low_confidence": <number>,
        "average_score": <number>
    }
    }
    """,
        output_key='validation_and_score_json',
        tools=[compliance_search_tool],
        generate_content_config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=15,
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
    print(f"Error initializing validate_and_score_agent: {e}")