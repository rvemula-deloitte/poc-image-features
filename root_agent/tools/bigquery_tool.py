"""BigQuery write tool for storing validation results."""

import os
from typing import Any

from google.cloud import bigquery
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from ..models import ConfidenceScoreRecord

# Singleton client instance
_bq_client: bigquery.Client | None = None


def _get_bigquery_client() -> bigquery.Client:
    """Get or create BigQuery client singleton."""
    global _bq_client
    if _bq_client is None:
        project_id =os.getenv("GOOGLE_CLOUD_PROJECT")
        _bq_client = bigquery.Client(project=project_id)
    return _bq_client


def _get_table_id() -> str:
    """Get fully qualified BigQuery table ID."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset = os.getenv("BQ_DATASET")
    table = os.getenv("BQ_TABLE")
    return f"{project_id}.{dataset}.{table}"


def write_to_bigquery(
    confidence_score_json: dict,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Write confidence score results to BigQuery.

    Args:
        confidence_score_json: A dictionary containing ALL of the following fields (all required):
                - mirakl_product_id (str): Unique product identifier from Mirakl.
                - status (str): Processing status, must be 'validated'.
                - confidence_score (float): AI-assigned quality score from 0 to 100.
                - validation_decision (str): Final decision — 'Approve' or 'Reject'.
                - ai_comment (str): Point-by-point reasoning behind the score and decision.
                - variant_group_code (str): VGC code from data.style_number.
                - brand (str): Product brand from data.brand.
                - title (str): Product title from data.title.
                - description (str): Product description from data.meta_description.
                - size (str): Product size variant from data.nrf_size.
                - colour (str): Product colour from data.display_color.
                - seller (str): Seller identifier — taken from sources[0].provider_code in the product data.

    Returns:
        Dictionary with status and result details.
    """
    # Extract session_id from ADK ToolContext (not exposed to the LLM)
    session_id = tool_context.session.id

    try:
        data = (
            confidence_score_json
            if isinstance(confidence_score_json, dict)
            else confidence_score_json.model_dump()
        )
        data.setdefault("session_id", session_id)
        record = ConfidenceScoreRecord.model_validate(data)
    except Exception as e:
        return {"status": "error", "message": f"Invalid confidence_score_json: {str(e)}"}

    try:
        client = _get_bigquery_client()
        table_id = _get_table_id()
        errors = client.insert_rows_json(table_id, [record.to_bq_row()])
        if errors:
            return {"status": "error", "message": f"BigQuery insert failed: {errors}"}
        return {
            "status": "success",
            "message": "Successfully inserted confidence score validation row(s)",
            "table": table_id,
            "rows_inserted": 1,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write to BigQuery: {str(e)}"}


def fetch_vgc_comparison_data(
    variant_group_code: str | None = None,
    brand: str | None = None,
    title: str | None = None,
    seller: str | None = None,
) -> dict[str, Any]:
    """
    Fetch existing BigQuery rows to allow AI-based VGC duplicate analysis.

    Runs two queries:
      1. Cross-VGC check — rows from the same seller sharing brand + title
         (catches identical products submitted under different VGC codes by the same seller).
      2. Intra-VGC fetch — ALL existing rows in the same VGC group
         (returns every variant so the AI can compare size + colour combinations).

    Args:
        variant_group_code: VGC code (style_number) of the incoming product.
        brand: Brand of the incoming product.
        title: Title of the incoming product.
        seller: Seller identifier (sources[0].provider_code) of the incoming product.

    Returns:
        Dictionary with:
            - cross_vgc_matches  (list[dict]): rows from same seller with same brand + title
            - intra_vgc_variants (list[dict]): all existing variants in the same VGC group
            - error (str): present only when the query fails
    """
    try:
        client = _get_bigquery_client()
        table_id = _get_table_id()
        result: dict[str, Any] = {
            "cross_vgc_matches": [],
            "intra_vgc_variants": [],
        }

        # ── Query 1: Cross-VGC check — same seller + brand + title ────────────
        if seller and brand and title and variant_group_code:
            q1 = f"""
                SELECT mirakl_product_id, variant_group_code, brand, title,
                       description, size, colour, seller, validation_decision
                FROM `{table_id}`
                WHERE seller             = @seller
                  AND LOWER(brand)       = LOWER(@brand)
                  AND LOWER(title)       = LOWER(@title)
                  AND LOWER(variant_group_code) != LOWER(@variant_group_code)
                LIMIT 20
            """
            cfg1 = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("seller",              "STRING", seller),
                bigquery.ScalarQueryParameter("brand",               "STRING", brand),
                bigquery.ScalarQueryParameter("title",               "STRING", title),
                bigquery.ScalarQueryParameter("variant_group_code",  "STRING", variant_group_code),
            ])
            result["cross_vgc_matches"] = [
                dict(row) for row in client.query(q1, job_config=cfg1).result()
            ]

        # ── Query 2: Intra-VGC fetch — ALL variants in the VGC group ────────
        # Returns everything so the AI can compare size + colour combinations.
        if variant_group_code:
            q2 = f"""
                SELECT mirakl_product_id, variant_group_code, brand, title,
                       description, size, colour, seller, validation_decision
                FROM `{table_id}`
                WHERE LOWER(variant_group_code) = LOWER(@variant_group_code)
                LIMIT 200
            """
            cfg2 = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("variant_group_code", "STRING", variant_group_code),
            ])
            result["intra_vgc_variants"] = [
                dict(row) for row in client.query(q2, job_config=cfg2).result()
            ]

        return result

    except Exception as e:
        return {
            "cross_vgc_matches": [],
            "intra_vgc_variants": [],
            "error": f"BigQuery fetch failed: {str(e)}",
        }


# Create the ADK FunctionTools
bigquery_write_tool = FunctionTool(func=write_to_bigquery)
vgc_fetch_tool = FunctionTool(func=fetch_vgc_comparison_data)
