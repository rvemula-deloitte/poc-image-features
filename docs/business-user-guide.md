# Business User Guide — Product Validation Pipeline (POC Image Features)

Version: 1.0  
Last Updated: April 6, 2026

1. Purpose and Audience

This guide explains, in business terms, what the Product Validation Pipeline does, how you will use it, and what value you can expect. It is intended for:
- Category Managers and Merchandising
- Brand/Content Governance and Compliance
- Vendor Management and Marketplace Operations
- Product Data Stewardship and Quality teams

No engineering background is required to use this guide.

2. What the application does (plain English)

The Product Validation Pipeline automatically reviews product listings before they go live, checking both images and text against internal rules and brand standards. It produces:
- An overall decision per product (Approve or Reject)
- A confidence score (0–100) indicating how likely the product is compliant
- A list of issues to fix (e.g., missing attributes, image not on white background, brand inconsistency)
- An AI-generated rationale that explains the decision

Validated results are written to analytics storage (BigQuery) so they can be viewed in dashboards or exported into spreadsheets.

3. Key outcomes and benefits

- Faster reviews: Parallel checks on images and attributes reduce manual effort.
- Consistency: Central, always-on enforcement of your policy and brand rules.
- Lower risk: Catch non-compliant content early (wrong product images, missing legal text, etc.).
- Actionable guidance: Clear, itemized issues for vendors or editors to fix.
- Measure and improve: Confidence scores and structured outcomes make it easy to track quality over time.
- Duplicate detection insights (optional): Spot cross-VGC submissions and duplicate size/colour variants using historical data.

4. What input data is needed

Provide a product record with:
- Identifiers: product_id (e.g., mirakl_product_id), SKU
- Title and Description: customer-facing text
- Images: main image URL (preferred), optional alternate image URLs
- Attributes: key fields relevant to your category (e.g., color, size, material)
- Category and Brand: used for category-specific checks and brand consistency
- Vendor (optional): used for vendor agreement checks, if applicable

Your integration or data team will prepare this in the expected JSON format for the pipeline. Sample payloads may be available in your project workspace to help you get started.

5. How it works at a glance

1) Compliance rules are searched
- The system pulls your policy/brand rules from an internal indexed knowledge base.

2) Image checks run
- Image dimensions and format are validated.
- Visual rules are assessed (e.g., plain background, no watermarks).
- Optional semantic check: the image content is compared against the product title/description to detect mismatches.

3) Attribute checks run
- Textual and structural rules are validated (e.g., required fields, banned terms, spelling).
- Brand consistency, variants logic, and category-specific requirements are verified.

4) Confidence score and decision
- Image and attribute outcomes are combined into a single score.
- A final decision is assigned: Approve or Reject.
- An AI comment explains the reasoning.

5) Results are saved
- Structured results are written to a BigQuery table for reporting.

6. What you will see in the results

Per product, you will typically see:
- status: validated
- validation_decision: Approve or Reject
- confidence_score (0–100)
- ai_comment: a short explanation in plain English
- image issues (if any): e.g., dimensions too small, background not compliant, image-content mismatch
- attribute issues (if any): e.g., missing required attribute, banned term, brand mismatch
- compliance rules applied: which categories of rules were used
- optional vgc insights (if enabled): cross-VGC matches and intra-VGC duplicate/combination checks
- session_id: tracking identifier for the validation run

7. Typical business workflows

- Triage and review queue
  - Sort by lowest confidence_score to prioritize risk.
  - Focus reviewers on items likely to be rejected without fixes.

- Vendor feedback loop
  - Share the issues list with vendors or content teams.
  - Provide the AI comment as quick context on what needs changing.

- Category/brand governance
  - Confirm that category-specific rules (e.g., apparel vs. lifestyle) are being enforced.
  - Spot trends by category or vendor (e.g., repeated brand naming issues).

- Measure quality over time
  - Track average confidence_score and approval rates by week, category, or vendor.
  - Use insights to refine rules and onboarding guidance.

- VGC duplicate review (if enabled)
  - Review cross-VGC matches (same seller + brand + title under different VGC codes) and action duplicates as needed.
  - Investigate intra-VGC duplicates (same size + colour) and correct catalog variants.

8. How to run it (options)

- Via a simple web UI (recommended for non-technical users)
  - Your team may provide a link to a secure internal UI.
  - Paste or upload product records to run a validation.
  - View results on-screen or export a summary (CSV/sheet/dashboard).

- Scheduled/automated runs (for operations teams)
  - Data/Engineering teams can schedule nightly or hourly batches.
  - Business users consume the resulting dashboards or shared reports.

Note: Exact access method may vary in your environment. Your data/engineering team will provide the URL or automation setup.

9. Interpreting the confidence score

Suggested thresholds (tune to your policy):
- 85–100: Auto-approve candidate (spot-check a sample if desired)
- 60–84: Manual review recommended (review issues; approve or request vendor fix)
- 0–59: Reject or send back for fixes (clear reasons provided in issues list)

These thresholds are starting points. Adjust them to balance speed (auto-approvals) and risk tolerance.

10. Data access and governance

- Where results live
  - A BigQuery table stores validated outcomes. Your analytics team will share the exact table details and access method.
  - Traceability metadata captured: variant_group_code, brand, title, description, size, colour, seller, session_id (columns may be nullable depending on configuration).
- Data sensitivity
  - The system stores only product metadata and results; no customer PII is expected.
- Access control
  - Access is gated via your organization’s standard IAM/permissions.
- Retention and auditability
  - Results can be retained for audit trails. Consult your data governance policy for retention timelines.

11. Frequently asked questions (FAQ)

- Q: What if a product has no main image?
  - A: The product will likely be flagged as non-compliant with a clear reason.

- Q: The model rejected a product I believe is fine. What do I do?
  - A: Use the issues list and AI comment to identify the blocking rule. If you still disagree, escalate to the governance team to refine rules or thresholds.

- Q: Are all categories supported?
  - A: Yes, but rule depth varies by category. Category managers can enhance category-specific rules over time.

- Q: Does it support multiple languages?
  - A: Yes for core checks, but certain language-specific rules (e.g., spelling) work best in supported languages. Check with your governance team for details.

- Q: How long does a validation take?
  - A: Typically seconds to a few minutes per batch, depending on batch size and image processing time.

- Q: Can we integrate directly with vendor portals?
  - A: This pilot focuses on validation and reporting. Integration into vendor workflows can be added in subsequent phases.

12. Known limitations and roadmap

- Visual nuance: Some edge cases (e.g., lifestyle shots vs. packshots) can be subjective and may require threshold tuning.
- New categories/attributes: If a category introduces new rules, initial accuracy may be lower until rules mature.
- Vendor education: Repeated issues often require clearer templates or vendor playbooks.
- Roadmap
  - Tunable confidence thresholds per category/brand.
  - Expanded semantic (image–text) checks where valuable.
  - Deeper integration with vendor feedback workflows.

13. Glossary

- Compliance rules: Your organization’s policy and brand standards for images, text, and structure.
- Confidence score (0–100): Overall quality and compliance indicator; higher is better.
- Approve/Reject: Final decision for a product’s readiness.
- Issues list: Itemized problems to fix (images or attributes).
- Products data: The product record provided to the system (IDs, text, images, attributes).

14. Support and ownership

- Business owner: Category/Content Governance lead
- Technical owner: Data/AI Engineering team
- How to get help: Submit a request through your internal help desk with the product ID, decision, and any questions. Include the confidence score and AI comment to speed up triage.

Appendix A — Example results (illustrative)

{
  "mirakl_product_id": "12345",
  "status": "validated",
  "validation_decision": "Reject",
  "confidence_score": 58,
  "ai_comment": "Main image background not compliant and 'Care instructions' missing.",
  "image_issues": [
    {"rule": "Background must be plain/white", "passed": false, "observation": "Patterned background detected"}
  ],
  "attribute_issues": [
    {"attribute": "care_instructions", "issue": "Required field missing"}
  ],
  "compliance_rules_applied": ["Image Issues", "Category Validation"]
}

Appendix B — Example product input (illustrative)

{
  "mirakl_product_id": "12345",
  "product_sku": "SKU-001",
  "title": "Men's Classic White Shirt",
  "description": "Slim-fit, cotton, machine-washable.",
  "category": "Ready to Wear",
  "brand": "Acme",
  "vendor": "Vendor A",
  "images": {
    "main_image": {"source": "https://example.com/image-main.jpg"},
    "alt_image_1": {"source": "https://example.com/image-alt-1.jpg"}
  },
  "attributes": {
    "color": "White",
    "size": "M",
    "material": "Cotton",
    "care_instructions": "Machine wash cold"
  }
}

Notes:
- Field names may vary depending on your integration. Your data team will provide the exact schema used in your environment.
