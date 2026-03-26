"""BigQuery read tool for fetching product records by product_id."""

import os
from typing import Any

from google.cloud import bigquery
from google.adk.tools import FunctionTool

# Singleton client instance for reads
_bq_read_client: bigquery.Client | None = None


def _get_bigquery_client() -> bigquery.Client:
    """Get or create BigQuery client singleton."""
    global _bq_read_client
    if _bq_read_client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        _bq_read_client = bigquery.Client(project=project_id)
    return _bq_read_client


def _get_product_table_id() -> str:
    """Get fully qualified BigQuery product table ID."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
    dataset = os.getenv("BQ_DATASET", "product_validation")
    table = os.getenv("BQ_PRODUCT_TABLE", "products")
    return f"{project_id}.{dataset}.{table}"


def get_product_from_bigquery(product_sku: str, table_id: str | None = None) -> dict[str, Any]:
    """Fetch a product row from BigQuery by product_sku."""
    if not product_sku:
        return {
            "status": "error",
            "message": "product_sku is required.",
        }

    try:
        client = _get_bigquery_client()
        if table_id is None:
            table_id = _get_product_table_id()

        query = f"SELECT * FROM `{table_id}` WHERE product_sku = @product_sku LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_sku", "STRING", product_sku),
            ]
        )
        job = client.query(query, job_config=job_config)
        rows = list(job.result())

        if not rows:
            return {
                "status": "success",
                "message": f"No product found for product_sku={product_sku}.",
                "product": None,
            }

        row = dict(rows[0])
        return {
            "status": "success",
            "message": "Product fetched successfully.",
            "product": row,
            "table": table_id,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch product from BigQuery: {str(e)}",
        }


bigquery_get_product_tool = FunctionTool(func=get_product_from_bigquery)
