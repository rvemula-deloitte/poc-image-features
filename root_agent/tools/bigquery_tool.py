"""BigQuery write tool for storing validation results."""

import os
from typing import Any

from google.cloud import bigquery
from google.adk.tools import FunctionTool

from ..models import ValidationRecord

# Singleton client instance
_bq_client: bigquery.Client | None = None


def _get_bigquery_client() -> bigquery.Client:
    """Get or create BigQuery client singleton."""
    global _bq_client
    if _bq_client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        _bq_client = bigquery.Client(project=project_id)
    return _bq_client


def _get_table_id() -> str:
    """Get fully qualified BigQuery table ID."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
    dataset = os.getenv("BQ_DATASET", "product_validation")
    table = os.getenv("BQ_TABLE", "validation_results")
    return f"{project_id}.{dataset}.{table}"


def write_to_bigquery(
    product_details: dict[str, Any],
    image_validation: dict[str, Any],
    attribute_validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Write validation results to BigQuery.

    Args:
        product_details: Original product data from the API.
        image_validation: Image dimension validation results.
        attribute_validation: Product attribute validation results.

    Returns:
        Dictionary with status and result details.
    """
    # Unwrap tool responses if they're nested
    if 'fetch_product_from_api_response' in product_details:
        product_details = product_details['fetch_product_from_api_response']
    
    if 'validate_image_response' in image_validation:
        image_validation = image_validation['validate_image_response']
    
    if 'Attribute_validation_response' in attribute_validation:
        attribute_validation = attribute_validation['Attribute_validation_response']
    
    record = ValidationRecord(
        product_details=product_details,
        image_validation=image_validation,
        attribute_validation=attribute_validation
    )
    row = record.to_bq_row()

    try:
        client = _get_bigquery_client()
        table_id = _get_table_id()

        errors = client.insert_rows_json(table_id, [row])

        if errors:
            return {
                "status": "error",
                "message": f"BigQuery insert failed: {errors}",
            }

        return {
            "status": "success",
            "message": "Successfully inserted validation record",
            "table": table_id,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write to BigQuery: {str(e)}",
        }


# Create the ADK FunctionTool
bigquery_write_tool = FunctionTool(func=write_to_bigquery)
