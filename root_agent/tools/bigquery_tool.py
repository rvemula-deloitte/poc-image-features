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
    confidence_score_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Write confidence score results to BigQuery.

    Args:
        confidence_score_json: Output JSON from Confidence Score Agent.

    Returns:
        Dictionary with status and result details.
    """
    if confidence_score_json is None:
        return {"status": "error", "message": "confidence_score_json is required"}

    # Accept nested tool outputs
    if isinstance(confidence_score_json, dict) and "validation_and_score_json" in confidence_score_json:
        confidence_score_json = confidence_score_json["validation_and_score_json"]

    if not isinstance(confidence_score_json, dict):
        return {"status": "error", "message": "confidence_score_json must be a JSON object"}

    results = confidence_score_json.get("results", [])
    if not isinstance(results, list):
        return {"status": "error", "message": "confidence_score_json.results must be a list"}

    rows = []
    for item in results:
        if not isinstance(item, dict):
            continue
        rows.append({
            "mirakl_product_id": item.get("mirakl_product_id"),
            "product_sku": item.get("product_sku"),
            "confidence_score": item.get("confidence_score"),
            "status": item.get("status"),
            "updated_at": item.get("updated_at"),
            "created_at": item.get("created_at"),
            "payload": item.get("payload", {}),
            "ai_comment": item.get("ai_comment"),
        })

    if not rows:
        return {"status": "error", "message": "No valid rows found in confidence_score_json.results"}

    try:
        client = _get_bigquery_client()
        table_id = _get_table_id()
        errors = client.insert_rows_json(table_id, rows)
        if errors:
            return {"status": "error", "message": f"BigQuery insert failed: {errors}"}
        return {
            "status": "success",
            "message": "Successfully inserted confidence score validation row(s)",
            "table": table_id,
            "rows_inserted": len(rows),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write to BigQuery: {str(e)}"}


# Create the ADK FunctionTool
bigquery_write_tool = FunctionTool(func=write_to_bigquery)
