import os
from datetime import datetime, timezone

from google.cloud import bigquery
from googleapiclient.discovery import build
from google.auth import default as google_auth_default


FINAL_STATUSES = ("ACCEPTED", "REJECTED")  # adjust if you have more finals


def get_bq_client():
    return bigquery.Client(project=os.environ["PROJECT_ID"])


def get_sheets_service():
    creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_last_export_ts(bq: bigquery.Client) -> datetime:
    project = os.environ["PROJECT_ID"]
    ds = os.environ["STATE_DATASET"]
    tbl = os.environ["STATE_TABLE"]
    pipeline = os.environ["PIPELINE_NAME"]

    sql = f"""
    SELECT last_export_ts
    FROM `{project}.{ds}.{tbl}`
    WHERE pipeline_name = @pipeline_name
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pipeline_name", "STRING", pipeline)]
        ),
    )
    rows = list(job.result())
    if not rows or rows[0]["last_export_ts"] is None:
        # first run: export everything already final (or choose an earlier cutoff)
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return rows[0]["last_export_ts"]


def write_last_export_ts(bq: bigquery.Client, new_ts: datetime) -> None:
    project = os.environ["PROJECT_ID"]
    ds = os.environ["STATE_DATASET"]
    tbl = os.environ["STATE_TABLE"]
    pipeline = os.environ["PIPELINE_NAME"]

    sql = f"""
    MERGE `{project}.{ds}.{tbl}` T
    USING (SELECT @pipeline_name AS pipeline_name, @last_export_ts AS last_export_ts) S
    ON T.pipeline_name = S.pipeline_name
    WHEN MATCHED THEN UPDATE SET last_export_ts = S.last_export_ts
    WHEN NOT MATCHED THEN INSERT (pipeline_name, last_export_ts) VALUES (S.pipeline_name, S.last_export_ts)
    """
    bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("pipeline_name", "STRING", pipeline),
                bigquery.ScalarQueryParameter("last_export_ts", "TIMESTAMP", new_ts),
            ]
        ),
    ).result()


def fetch_changed_rows(bq: bigquery.Client, last_ts: datetime):
    project = os.environ["PROJECT_ID"]
    ds = os.environ["BQ_DATASET"]
    tbl = os.environ["BQ_TABLE"]

    sql = f"""
    SELECT
      product_id,
      status,
      reason_code,
      status_updated_at
    FROM `{project}.{ds}.{tbl}`
    WHERE status IN UNNEST(@final_statuses)
      AND status_updated_at > @last_export_ts
    ORDER BY status_updated_at ASC
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("final_statuses", "STRING", list(FINAL_STATUSES)),
                bigquery.ScalarQueryParameter("last_export_ts", "TIMESTAMP", last_ts),
            ]
        ),
    )
    return list(job.result())


def ensure_header(sheets, sheet_id: str, tab: str):
    # Writes header into row 1 if empty (simple check)
    rng = f"{tab}!A1:D1"
    resp = sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=rng).execute()
    values = resp.get("values", [])
    if values:
        return
    header = [["product_id", "status", "reason_code", "status_updated_at"]]
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=rng,
        valueInputOption="RAW",
        body={"values": header},
    ).execute()


def append_rows_to_sheet(sheets, sheet_id: str, tab: str, rows):
    if not rows:
        return
    values = [
        [r["product_id"], r["status"], r.get("reason_code"), r["status_updated_at"].isoformat()]
        for r in rows
    ]
    sheets.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab}!A:D",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def main():
    bq = get_bq_client()
    sheets = get_sheets_service()

    sheet_id = os.environ["SHEET_ID"]
    tab = os.environ.get("SHEET_TAB", "FinalStatus")

    last_ts = read_last_export_ts(bq)
    changed = fetch_changed_rows(bq, last_ts)

    ensure_header(sheets, sheet_id, tab)
    append_rows_to_sheet(sheets, sheet_id, tab, changed)

    if changed:
        new_ts = max(r["status_updated_at"] for r in changed)
        write_last_export_ts(bq, new_ts)

    print(f"Exported {len(changed)} rows. last_export_ts was {last_ts.isoformat()}")


if __name__ == "__main__":
    main()