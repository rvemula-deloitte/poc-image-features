"""Standalone BigQuery product SKU fetcher script."""

import argparse
import json
import os
from typing import Any

from google.cloud import bigquery


_bq_read_client: bigquery.Client | None = None


def _get_bigquery_client() -> bigquery.Client:
    global _bq_read_client
    if _bq_read_client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        _bq_read_client = bigquery.Client(project=project_id)
    return _bq_read_client


def _get_product_table_id() -> str:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
    dataset = os.getenv("BQ_DATASET", "product_validation")
    table = os.getenv("BQ_PRODUCT_TABLE", "products")
    return f"{project_id}.{dataset}.{table}"


def get_product_from_bigquery(product_sku: str, table_id: str | None = None) -> dict[str, Any]:
    if not product_sku:
        return {"status": "error", "message": "product_sku is required."}

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

        return {
            "status": "success",
            "message": "Product fetched successfully.",
            "product": dict(rows[0]),
            "table": table_id,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch product from BigQuery: {str(e)}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch product by SKU from BigQuery")
    parser.add_argument("product_sku", help="Product SKU to fetch")
    parser.add_argument("--table-id", default=None, help="Optional fully-qualified BigQuery table id")
    args = parser.parse_args()

    result = get_product_from_bigquery(args.product_sku, table_id=args.table_id)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
