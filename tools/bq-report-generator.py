from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook

# If this import fails in your Composer image, tell me your Composer version
# and providers package version; I’ll adjust to the correct hook/operator path.
from airflow.providers.google.suite.hooks.sheets import GoogleSheetsHook


DAG_ID = "bq_final_status_to_sheets"

DEFAULT_ARGS = {"owner": "data-eng"}

# Airflow Variables (set in Composer UI: Admin -> Variables)
# Required:
#   gcp_project_id
#   bq_dataset
#   bq_table
#   state_dataset
#   state_table
#   pipeline_name
#   sheet_id
#   sheet_tab
#
# Optional:
#   final_statuses  (comma-separated; default: ACCEPTED,REJECTED)
#   gcp_conn_id     (default: google_cloud_default)

with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2025, 1, 1),
    schedule="*/10 * * * *",  # every 10 minutes (change as needed)
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["bq", "sheets", "export"],
) as dag:

    @task()
    def read_last_export_ts() -> str:
        gcp_conn_id = Variable.get("gcp_conn_id", default_var="google_cloud_default")
        project = Variable.get("gcp_project_id")
        state_dataset = Variable.get("state_dataset")
        state_table = Variable.get("state_table")
        pipeline_name = Variable.get("pipeline_name")

        bq = BigQueryHook(gcp_conn_id=gcp_conn_id, use_legacy_sql=False)

        sql = f"""
        SELECT last_export_ts
        FROM `{project}.{state_dataset}.{state_table}`
        WHERE pipeline_name = @pipeline_name
        """
        rows = bq.get_records(
            sql=sql,
            parameters=[{"name": "pipeline_name", "parameterType": {"type": "STRING"}, "parameterValue": {"value": pipeline_name}}],
        )

        if not rows or rows[0][0] is None:
            return datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat()
        # rows[0][0] is typically a datetime; normalize to ISO string for XCom
        ts = rows[0][0]
        if isinstance(ts, str):
            return ts
        return ts.replace(tzinfo=timezone.utc).isoformat()

    @task()
    def fetch_changed_rows(last_export_ts_iso: str) -> dict:
        gcp_conn_id = Variable.get("gcp_conn_id", default_var="google_cloud_default")
        project = Variable.get("gcp_project_id")
        bq_dataset = Variable.get("bq_dataset")
        bq_table = Variable.get("bq_table")

        final_statuses_csv = Variable.get("final_statuses", default_var="ACCEPTED,REJECTED")
        final_statuses = [s.strip() for s in final_statuses_csv.split(",") if s.strip()]

        bq = BigQueryHook(gcp_conn_id=gcp_conn_id, use_legacy_sql=False)

        # BigQuery named parameters: last_export_ts + array of final statuses
        sql = f"""
        SELECT
          product_id,
          status,
          reason_code,
          status_updated_at
        FROM `{project}.{bq_dataset}.{bq_table}`
        WHERE status IN UNNEST(@final_statuses)
          AND status_updated_at > @last_export_ts
        ORDER BY status_updated_at ASC
        """

        # BigQueryHook.get_records supports query parameters in "parameters" for the Jobs API
        parameters = [
            {
                "name": "final_statuses",
                "parameterType": {"type": "ARRAY", "arrayType": {"type": "STRING"}},
                "parameterValue": {"arrayValues": [{"value": s} for s in final_statuses]},
            },
            {
                "name": "last_export_ts",
                "parameterType": {"type": "TIMESTAMP"},
                "parameterValue": {"value": last_export_ts_iso},
            },
        ]

        rows = bq.get_records(sql=sql, parameters=parameters)

        # rows: List[Tuple[product_id, status, reason_code, status_updated_at]]
        out = []
        max_ts = None
        for (product_id, status, reason_code, status_updated_at) in rows:
            ts = status_updated_at
            if not isinstance(ts, str):
                # Convert datetime to ISO; ensure timezone
                ts = ts.replace(tzinfo=timezone.utc).isoformat()
            out.append([product_id, status, reason_code, ts])
            max_ts = ts if (max_ts is None or ts > max_ts) else max_ts

        return {"rows": out, "new_last_export_ts": max_ts}

    @task()
    def append_to_sheet(payload: dict) -> dict:
        rows = payload["rows"]
        if not rows:
            return payload

        sheet_id = Variable.get("sheet_id")
        tab = Variable.get("sheet_tab", default_var="FinalStatus")
        gcp_conn_id = Variable.get("gcp_conn_id", default_var="google_cloud_default")

        sheets = GoogleSheetsHook(gcp_conn_id=gcp_conn_id)

        # Optional: write header if sheet is empty (simple check)
        header = ["product_id", "status", "reason_code", "status_updated_at"]
        existing = sheets.get_values(spreadsheet_id=sheet_id, range_=f"{tab}!A1:D1")
        if not existing or not existing[0]:
            sheets.update_values(
                spreadsheet_id=sheet_id,
                range_=f"{tab}!A1:D1",
                values=[header],
            )

        # Append data
        sheets.append_values(
            spreadsheet_id=sheet_id,
            range_=f"{tab}!A:D",
            values=rows,
        )
        return payload

    @task()
    def write_last_export_ts(payload: dict) -> None:
        new_ts = payload["new_last_export_ts"]
        if not new_ts:
            return

        gcp_conn_id = Variable.get("gcp_conn_id", default_var="google_cloud_default")
        project = Variable.get("gcp_project_id")
        state_dataset = Variable.get("state_dataset")
        state_table = Variable.get("state_table")
        pipeline_name = Variable.get("pipeline_name")

        bq = BigQueryHook(gcp_conn_id=gcp_conn_id, use_legacy_sql=False)

        sql = f"""
        MERGE `{project}.{state_dataset}.{state_table}` T
        USING (SELECT @pipeline_name AS pipeline_name, @last_export_ts AS last_export_ts) S
        ON T.pipeline_name = S.pipeline_name
        WHEN MATCHED THEN UPDATE SET last_export_ts = S.last_export_ts
        WHEN NOT MATCHED THEN INSERT (pipeline_name, last_export_ts) VALUES (S.pipeline_name, S.last_export_ts)
        """

        parameters = [
            {"name": "pipeline_name", "parameterType": {"type": "STRING"}, "parameterValue": {"value": pipeline_name}},
            {"name": "last_export_ts", "parameterType": {"type": "TIMESTAMP"}, "parameterValue": {"value": new_ts}},
        ]
        bq.run(sql=sql, parameters=parameters)

    last_ts = read_last_export_ts()
    payload = fetch_changed_rows(last_ts)
    payload2 = append_to_sheet(payload)
    write_last_export_ts(payload2)