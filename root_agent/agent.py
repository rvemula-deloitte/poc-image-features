"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext

from .sub_agents.compliance_search_agent import compliance_search_agent
from .sub_agents.validate_image_agent import validate_image_agent
from .sub_agents.validate_attribute_agent import validate_attribute_agent
from .sub_agents.validate_vgc_agent import validate_vgc_agent
from .sub_agents.confidence_score_agent import confidence_score_agent
from .sub_agents.bigquery_write_agent import bigquery_write_agent


def _store_product_data_in_state(callback_context: CallbackContext) -> None:
    """Store the latest user message into state["products_data"] as-is."""
    for event in reversed(callback_context.session.events):
        parts = getattr(event.content, "parts", None) or []
        text = next((p.text for p in parts if getattr(p, "text", None)), "")
        if text:
            callback_context.state["products_data"] = text
            break

# Parallel agent: image validation + attribute validation + VGC duplicate check run concurrently
validation_parallel_agent = ParallelAgent(
    name="validation_parallel_agent",
    description="Runs image validation, attribute validation, and VGC duplicate check in parallel",
    sub_agents=[
        validate_image_agent,        # -> image_validation_json
        validate_attribute_agent,    # -> attribute_validation_json
        # Need to change confidence score agent system prompt whn this is uncommented.
        validate_vgc_agent,          # -> vgc_validation_json
    ],
)

# Root Sequential Agent - validates and scores products
try:
    root_agent = SequentialAgent(
        name="product_validation_pipeline",
        description="Sequential agent pipeline for product extraction, validation, and storage",
        before_agent_callback=_store_product_data_in_state,
        sub_agents=[
            compliance_search_agent,    # Step 1: Fetch image compliance rules -> compliance_search_result
            validation_parallel_agent,  # Step 2: Image + Attribute validation in parallel
            confidence_score_agent,     # Step 3: Combine both -> validation_and_score_json
            bigquery_write_agent,       # Step 4: Write confidence score results to BigQuery
        ],
    )
except Exception as e:
    print(f"Error initializing root agent: {e}")
