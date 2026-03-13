"""Embedding-based image validation agent using Vertex AI MultiModalEmbedding."""

from google.adk.agents import LlmAgent
from ..tools.embedding_validation_tool import validate_image_embedding_tool


validate_image_embedding_agent = LlmAgent(
    name='ImageEmbeddingValidatorAgent',
    model='gemini-2.5-flash',
    description='Validate product images against their descriptions using embeddings',
    instruction='''
You are an image embedding validation agent that checks if product images match their titles and descriptions.

Call the `validate_image_embedding` tool with:
- products: Pass the products_data array directly
- similarity_threshold: (optional) Minimum similarity score (default: 0.70)

This tool uses Vertex AI MultiModalEmbedding to compare image content with product text descriptions.

Return ONLY the JSON from the tool. No extra text.
''',
    output_key='image_validation_json',
    tools=[validate_image_embedding_tool]
)
