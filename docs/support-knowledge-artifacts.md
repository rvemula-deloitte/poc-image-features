# Support Knowledge Artifacts — Product Validation Pipeline (POC Image Features)

Version: 1.0  
Last Updated: April 6, 2026

Purpose and Audience
This document equips L1/L2/L3 support, operations, and SRE teams to run, triage, and maintain the Product Validation Pipeline. It consolidates runbooks, troubleshooting guides, operational procedures, and templates.

Related Documentation
- Technical Design: docs/technical_design_document.md
- Business User Guide: docs/business-user-guide.md
- README (setup and usage): README.md

System Overview (What to Support)
- Framework: Google Agent Development Kit (ADK)
- Core pipeline (Sequential + Parallel):
  1) ComplianceSearchAgent (rules via Vertex AI Search)
  2) Parallel:
     - ImageValidatorAgent (dimensions + visual checks)
     - ValidateAttributeAgent (textual/structural checks)
     - VGCDuplicateCheckAgent (optional: cross/intra VGC insights)
  3) ConfidenceScoreAgent (score + decision + session_id)
  4) BigQueryWriteAgent (persist results to BigQuery)
- Key outputs (state keys):
  - compliance_search_result, image_validation_json, attribute_validation_json,
    validation_and_score_json, bigquery_result, (optional) vgc_validation_json
- Storage: BigQuery table: {GOOGLE_CLOUD_PROJECT}.{BQ_DATASET}.{BQ_TABLE}

Ownership and Contacts
- Business Owner: Category/Content Governance Lead
- Technical Owner: Data/AI Engineering
- On-call Rotation: <fill team name/rota link>
- Slack/Teams Channel: <fill channel>
- Email DL: <fill DL>
- Vendors/Partners: GCP Support (BigQuery, Vertex AI), Internal Platform/SRE

Environments and Access
- Local/dev usage: ADK CLI or Web UI
  - CLI: adk run root_agent
  - Web: adk web then open http://localhost:8000 (pipeline: product_validation_pipeline)
- Credentials: Google Application Default Credentials (ADC)
  - gcloud auth application-default login
- Environment variables (.env):
  - GOOGLE_CLOUD_PROJECT
  - BQ_DATASET (e.g., product_validation)
  - BQ_TABLE (e.g., validation_results)
- IAM (minimum effective permissions):
  - BigQuery Data Editor on {PROJECT}.{BQ_DATASET}
  - Vertex AI User (Model/Endpoints) and Vertex AI Search/Discovery Engine Reader
  - Storage/Network as required for image downloads

Runbooks

1) First Response Checklist (Any Alert/Issue)
- Is the pipeline reachable?
  - CLI: adk run root_agent (does it start?)
  - Web: adk web → http://localhost:8000 loads?
- Are credentials valid? gcloud auth application-default print-access-token
- Are env vars set? type .env (Windows) or cat .env (Linux/macOS)
- Is BigQuery reachable? Check dataset/table exists in console or via bq ls
- Any recent code/config change? Review last commits / deployment notes
- Impact radius? Single user, single product, or system-wide?

2) Start/Stop and Health
- Start CLI (local): 
  - adk run root_agent
- Start Web UI (local):
  - adk web
  - Open http://localhost:8000 → select product_validation_pipeline
- Basic health signal:
  - Submit a known-good payload (session_payload_min.json) and observe results:
    - validation_and_score_json produced
    - bigquery_result.status == "success"

3) Standard Validation Flow (Operator)
- Obtain products_data (JSON list or JSON string of a list)
- Provide to the pipeline (CLI/Web) as the last message
  - The pipeline captures last message into products_data via before_agent_callback
- Confirm end-to-end:
  - compliance_search_result populated
  - image_validation_json and attribute_validation_json created
  - validation_and_score_json has status=validated, decision, score, ai_comment, session_id
  - bigquery_result shows rows_inserted=1

4) Enabling Optional VGC Duplicate Insights (Operator/Engineer)
- File: root_agent/agent.py
  - In validation_parallel_agent, uncomment validate_vgc_agent in sub_agents
- File: root_agent/sub_agents/confidence_score_agent.py
  - (Optional) Extend prompt to read vgc_validation_json if you want VGC findings to influence score/decision
- Ensure BigQuery table has historical rows to compare against
- Confirm vgc_validation_json is produced

Troubleshooting Guides (Common Issues)

A) BigQuery insert failed
- Symptom: bigquery_result.status == "error"
- Likely causes:
  - Table not found or wrong dataset/table name
  - Missing ADC or insufficient IAM
  - Schema mismatch (missing columns)
- Actions:
  - Verify .env: GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE
  - Confirm table exists; if missing, create using README schema
  - Check IAM: BigQuery Data Editor on dataset
  - Review error detail in message: "... BigQuery insert failed: ..."

B) Vertex AI Search errors (ComplianceSearchAgent)
- Symptom: compliance_search_result missing or empty
- Likely causes:
  - Wrong datastore id or permissions
- Actions:
  - Check datastore id configured in root_agent/sub_agents/compliance_search_agent.py
  - Validate Vertex AI Search/Discovery Engine access for service account
  - Test minimal query via console if available

C) Image download/parse failures (get_image_dimensions_tool)
- Symptom: image_validation_json contains error for width/height
- Likely causes:
  - Unreachable URLs, timeouts, corrupted images, unsupported formats
- Actions:
  - Verify image URLs are reachable from environment
  - Retry with alternate image URLs if provided
  - Increase timeout if consistently borderline (code change)

D) products_data not captured
- Symptom: agents see empty/missing products_data
- Likely cause:
  - Last message was not a JSON list (or JSON string of a list)
- Actions:
  - Re-send a properly formatted products_data
  - Use provided sample: session_payload_min.json / session_payload_fixed.json

E) Session ID missing in results
- Symptom: validation_and_score_json lacks session_id
- Likely cause:
  - before_agent_callback not executed or session object missing
- Actions:
  - Ensure running via ADK (CLI or Web) so session exists
  - Review root_agent/sub_agents/confidence_score_agent.py callback

F) VGC fetch slow or empty
- Symptom: vgc_validation_json missing or empty; long query times
- Likely causes:
  - No historical data; wrong table; heavy dataset scans
- Actions:
  - Validate table id used by vgc_fetch_tool (derived from env vars)
  - Confirm historical rows exist for given seller/brand/title/VGC
  - Add filters/limits where appropriate (code-level tuning)

G) Permission/IAM issues
- Symptom: Access denied for BigQuery or Vertex AI
- Actions:
  - Confirm service account used by ADC; check roles
  - Re-run gcloud auth application-default login with correct account
  - Validate org-level restrictions (VPC-SC, SCP)

Operational Procedures

1) Schema Migration (BigQuery)
- Preferred: additive (new nullable columns)
- Steps:
  - Stage change in lower env
  - Update README schema example if columns are added
  - Apply DDL alteration (ADD COLUMN)
  - Smoke test single insert from dev pipeline

2) Backfill/Replay
- When a run failed to write rows:
  - Export validation_and_score_json (if available) and re-call write_to_bigquery
  - Alternatively, re-run pipeline with saved payload (session_payload_fixed.json)
  - Verify bigquery_result success and row presence

3) Key/Secret Rotation
- ADC (local) uses user credentials; rotation is user-driven
- For service accounts:
  - Rotate keys in IAM
  - Re-deploy secret to runtime or workstation
  - Validate by executing a test write

4) Change Management (Pre-Deploy Checklist)
- Tests passing locally (unit/integration if present)
- .env updated for new config (if required)
- Backwards-compatible BQ schema changes applied
- Optional features (VGC) toggled intentionally and documented
- Post-deploy smoke test: single product run and confirm row in BQ

Observability and Monitoring

Recommended Metrics
- Pipeline run success rate (%)
- BigQuery insert latency and error rate
- Vertex AI Search query latency/errors
- Image download timeout/error rate
- Average confidence_score by day/category/vendor
- Approve/Reject distribution over time

Logging Guidance
- Use structured logs for:
  - product_id/mirakl_product_id
  - session_id
  - decision, confidence_score
  - counts of issues found by category
  - tool errors (BigQuery/HTTP)
- ConfidenceScoreAgent prints session id; consolidate into a standard logger if centralized logging is added later

Dashboards and Queries
- Use BigQuery to create Looker Studio or Dataform dashboards
- Example query (daily approvals):
```
SELECT
  DATE(_PARTITIONTIME) AS run_date,
  COUNTIF(validation_decision = 'Approve') AS approved,
  COUNTIF(validation_decision = 'Reject')  AS rejected,
  AVG(confidence_score) AS avg_conf
FROM `your-project.product_validation.validation_results`
GROUP BY run_date
ORDER BY run_date DESC;
```

Security and Compliance
- No customer PII expected; stores product metadata and validation outputs
- Enforce least-privilege IAM for service accounts
- Follow org retention policies for validation results (auditability)

Ticket Templates

1) Incident Ticket (Example)
- Title: [PVP] Severity-<1/2/3> — <Short issue description>
- Impact: Users/products affected, blast radius
- When started: Date/time
- Symptoms: Errors/logs, screenshots
- Recent changes: Code/config/deployment
- Steps taken: What has been tried
- Owner/Assignee: On-call name
- Next action: Proposed steps and ETA

2) Change Request (Example)
- Title: [PVP] Enable VGC branch in parallel agent
- Summary: What/why
- Risk: Low/Medium/High
- Rollback: How to revert
- Validation plan: Post-change smoke tests
- Schedule/Approvals: Window and approvers

3) Postmortem (Example)
- Summary
- Timeline
- Root Cause
- Impact
- Detection and Response
- What Went Well / What Didn’t
- Action Items (owners, due dates)

Incident Classification (Guide)
- Sev-1: System unavailable; widespread write failures; data loss
- Sev-2: Major functionality degraded; elevated error rates
- Sev-3: Minor issues; workarounds available; localized failures

Operational Tips and FAQs

- How do we quickly validate end-to-end?
  - Use adk web, run a single known-good payload, confirm bigquery_result success
- How do we know which rules were applied?
  - compliance_search_result includes categories and references; see Technical Design
- Can we auto-approve based on score?
  - Business policy; consider thresholds (see Business User Guide)
- Where do we see optional VGC insights?
  - In vgc_validation_json (if enabled) and in BQ if you persist those insights downstream

Glossary
- VGC: Variant Group Code (style_number)
- ADC: Application Default Credentials
- L1/L2/L3: Support levels (first-line to engineering)
- ADK: Google Agent Development Kit

Quick Reference (Commands)
- Authenticate ADC:
```
gcloud auth application-default login
```
- Run CLI:
```
adk run root_agent
```
- Run Web:
```
adk web
```
- Open local web (Windows):
```
start http://localhost:8000
```

Appendix: File Pointers
- Root orchestrator: root_agent/agent.py
- Confidence Score Agent: root_agent/sub_agents/confidence_score_agent.py
- Attribute Validator: root_agent/sub_agents/validate_attribute_agent.py
- Image Validator: root_agent/sub_agents/validate_image_agent.py
- Optional VGC Agent: root_agent/sub_agents/validate_vgc_agent.py
- BigQuery Tools: root_agent/tools/bigquery_tool.py

Placeholders To Fill (Project-Specific)
- On-call rota link, DLs, chat channels
- Exact Vertex AI Search datastore id and project/region
- Final BigQuery table id with project/dataset/table
- Any org-specific SLAs/SLOs, retention timelines
