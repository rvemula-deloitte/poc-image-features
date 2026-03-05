"""URL Context Agent - fetches and analyses an image URL based on a specific query."""

from google.adk.agents import LlmAgent
from google.adk.tools import url_context


url_context_agent = LlmAgent(
    name='UrlContextAgent',
    model='gemini-2.5-flash',
    description='Fetch an image from a URL and answer specific questions about it (dimensions, quality, content, etc.)',
    instruction='''
You are an Image URL Analysis Agent.

You will receive:
1. An image URL
2. A query describing what to inspect or measure about that image

Steps:
1. Use the `url_context` tool to load the image from the provided URL.
2. Answer ONLY what the query asks for — do not produce unrelated analysis.
3. Return your findings as JSON:

{
    "url": "<the image URL>",
    "query": "<what was asked>",
    "findings": {
        "<key>": "<value>"
    },
    "summary": "<one-line summary of the findings>"
}

Examples of what callers may ask:
- "What is the image format (JPEG, PNG, etc.)?"
- "Does the image have a white background?"
- "Is the product centred in the frame?"

Only use the `url_context` tool. Do not hallucinate pixel values — report only what you can observe.
''',
    output_key='url_context_result',
    tools=[url_context],
)
