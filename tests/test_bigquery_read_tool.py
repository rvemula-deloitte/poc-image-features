import pytest

from tools import bigquery_read_tool


class FakeQueryJob:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return self._rows


class FakeBigQueryClient:
    def __init__(self):
        self.last_query = None

    def query(self, query, job_config=None):
        self.last_query = query
        return FakeQueryJob([{"product_sku": "sku-123", "name": "Test Product"}])


def test_get_product_from_bigquery_missing_sku():
    result = bigquery_read_tool.get_product_from_bigquery("")
    assert result["status"] == "error"
    assert "required" in result["message"]


def test_get_product_from_bigquery_found(monkeypatch):
    fake_client = FakeBigQueryClient()
    monkeypatch.setattr(bigquery_read_tool, "_get_bigquery_client", lambda: fake_client)

    result = bigquery_read_tool.get_product_from_bigquery("sku-123", table_id="project.dataset.products")

    assert result["status"] == "success"
    assert result["product"] is not None
    assert result["product"]["product_sku"] == "sku-123"
    assert "product_sku = @product_sku" in fake_client.last_query


def test_write_to_bigquery_confidence_score_json(monkeypatch):
    from root_agent.tools import bigquery_tool

    class FakeClient:
        def insert_rows_json(self, table_id, rows):
            self.last_rows = rows
            return []

    fake_client = FakeClient()
    monkeypatch.setattr(bigquery_tool, "_get_bigquery_client", lambda: fake_client)

    sample = {
        "results": [
            {
                "mirakl_product_id": "id-1",
                "product_sku": "sku-1",
                "confidence_score": 100,
                "updated_at": "2025-01-01T00:00:00Z",
                "created_at": "2025-01-01T00:00:00Z",
                "status": "Validated",
                "payload": {},
                "ai_comments": "All good",
            }
        ]
    }

    result = bigquery_tool.write_to_bigquery(confidence_score_json=sample)
    assert result["status"] == "success"
    assert result["rows_inserted"] == 1
    assert fake_client.last_rows[0]["product_sku"] == "sku-1"
