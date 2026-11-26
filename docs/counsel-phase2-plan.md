# Counsel Phase 2 — smallest secure implementation (proposal)

Independent Counsel addition to CaseCite (Copyright 2026 Thomas Unise, Apache-2.0). Proposal only: nothing here is implemented yet. Every new table is additive; migrations run only in development and CI until a release is approved. Fictional data only.

## Principle: extend, don't rebuild

| Need | Existing CaseCite piece to reuse |
|---|---|
| Matter scoping, sharing, walls | `Matter`, `MatterMember`, `MatterWall`, `_matter_deps.py` |
| Tenant isolation in the database | `app/rls.py` `OWNED_TABLES` / `CHILD_TABLES` (migration 024/027 policies), `tests/test_rls_postgres.py` |
| Citation verification | `services/quote_verify.py` (verbatim quote must be found in the source text), `rag/claim_grounding.py` |
| Document storage, extraction, OCR, deletion, legal hold, retention | `services/documents.py`, document registry (025), hold/retention (022) |
| Human approval | workflow `approval` step (`services/workflows/steps.py`), run history |
| Reports | `contract_analysis/report.py` (python-docx, reportlab already pinned) |
| Audit | `services/audit.py` `log_event`, fail-closed event list |
| AI provider policy / BYOK / notice | `provider_policy.py`, `llm_clients.py`, `ai_notice.py` |

## Data model (one additive migration, 028)

Owned (added to `OWNED_TABLES`, `matter_id` **NOT NULL** — a patent workspace always belongs to a matter):
- `patent_workspaces(id, owner_id, matter_id, title, status, created_at, updated_at)`

Children (added to `CHILD_TABLES`, visible only when the parent is):
- `invention_disclosures(id, workspace_id, version, fields JSON, content_sha256, created_by, created_at)`. This is append-only, and each save is a new version, so approvals can point at exact content. The free-text fields are encrypted with the existing `services/encryption.py`, the same way other sensitive columns are.
- `claim_elements(id, workspace_id, claim_no, element_no, text)`
- `claim_mappings(id, element_id, reference_document_id, quote, start, end, page, status, verified bool, note)`. This is multi-reference: there is one row per (element, reference). `reference_document_id` points at an existing Document filed under the same matter. `verified` is set only by `quote_verify` against that document's stored text, never by the model or the client.
- `patent_reviews(id, workspace_id, subject_type, subject_id, subject_sha256, reviewer_id, decision, note, created_at)`. This is append-only, and the approval is bound to the hash of what was approved.

Public, read-only, not tenant data (no RLS, served to every signed-in user):
- `legal_sources(id, name, edition, revision, published_on, source_url, fetched_at)`
- `legal_source_sections(id, source_id, section_id, title, text, text_sha256, url, revision_note)`

## PR 1 as built (differs from the sketch above)

PR 1 ships the smallest safe slice; the rest of the model above lands with the PR that needs it.
- `patent_workspaces(id, owner_id, matter_id NOT NULL, title, reviewer_notes_enc, created_at, updated_at)`: no `status` column yet (nothing reads it until approvals, PR 5).
- `invention_disclosures` as sketched (append-only, `fields_enc` encrypted, `content_sha256` of the canonical plaintext; an unchanged save adds no version).
- `claim_elements(id, workspace_id, position, payload_enc, status, verified, updated_by, updated_at)` holds one chart row as the current UI does (element, disclosure support, one candidate reference, pinpoint passage, notes), encrypted as one payload. The multi-reference `claim_mappings` table, with `reference_document_id` and offsets, is deferred to PR 3, where a passage can be checked against an indexed document. Until then `verified` is always false: the request schema forbids the field, and only server-side verification may set it.
- `patent_reviews` and the `patent.write` / `patent.approve` permissions are deferred to PRs 4–5. PR 1 gates every route with the existing `contracts.use`. Only the owner writes or deletes, members read, and everyone else gets 404.
- The tables are in `rls.OWNED_TABLES` / `CHILD_TABLES` (migration 028 installs their policies on PostgreSQL), and in the wall, offboarding-transfer and account-purge paths.

## PR 2 as built

- `legal_sources(id, name, edition, revision, published_on, source_url, created_at, fetched_at)` and `legal_source_sections(id, source_id, section_id, title, text, text_sha256, url, revision_note, fetched_at)` (migration 029). Public text, so these tables are not tenant data and have no RLS.
- **Ingestion** is `scripts/ingest_mpep.py`, run only by an operator; the app never fetches.
  - Only `https://www.uspto.gov/web/offices/pac/mpep/*.html` is allowed (`check_mpep_url`). Redirects are refused, and pages are fetched one at a time with a delay between them.
  - Pages can come from a chapter index, a list of URLs, or a directory of saved pages.
  - The operator must state the edition and revision; nothing is guessed. Each section keeps the revision marker printed in its heading.
  - Re-running the same revision adds only missing sections. If a section's text changed under the same revision, it is reported as a conflict and never rewritten. A new revision becomes a new source.
  - `--dry-run` parses and reports without storing. The exit code is 1 when conflicts or pages with no sections were found.
- **Parser**: it reads headings of the form `NUMBER Title [R-MM.YYYY]` and stops each section at the next heading, a reserved slot, `[top]` or the chapter table of contents. The layout was taken from the live pages, but the tests use only synthetic fixtures (section numbers 99xx), so whether it parses current live pages correctly is unverified until an operator's first run. An unfamiliar layout yields zero sections, which are reported, rather than guesses.
- **Retrieval** differs from the sketch: it is plain SQL search over the stored sections (by section number, or by words that must all match), not the lexical index or vector store, so the tenant scope guard is untouched. PR 3 decides whether generation needs vector retrieval over a separate public namespace.
- **API**: `GET /legal-sources`, `GET /legal-sources/sections?q=`, `GET /legal-sources/sections/{id}`. These are read-only and need `tools.research` (viewers included). Every result carries the official URL, edition and revision, the section's revision marker, the fetch time and the text's SHA-256.
- **UI**: IP Research has a "Stored MPEP text" panel. It searches only on submit, and links each excerpt to its official page.

## Capabilities, in PR order

1. **Persistent Patent Studio.** Replace in-memory state with the tables above via a `routers/patent.py` that uses the matter dependency for every route. Disclosures, claim elements and mappings are saved and versioned. Pinpoint mappings are verified server-side with `quote_verify`. Tests: CRUD, and cross-user and cross-matter denial extending `test_matter_isolation.py`. The new tables are added to `test_rls_postgres.py`.
2. **MPEP ingestion and retrieval.** `scripts/ingest_mpep.py` is an operator-run job that fetches only `https://www.uspto.gov/web/offices/pac/mpep/` pages and records edition, revision, URL, fetch time and a SHA-256 per section. It is idempotent per revision, and a new revision adds rows instead of overwriting. Retrieval reuses `lexical_index` and the vector store under a separate read-only "public sources" namespace that can never be mixed with tenant scopes; the scope guard is extended accordingly. There is no network access in tests: fixtures are small synthetic pages clearly marked as test fixtures.
3. **AI-assisted analysis with section-level citations.** This reuses RAG generation with a prompt that may cite only retrieved sections. Every citation must carry `section_id` + revision + a verbatim quote that `quote_verify` finds in the stored section text. Anything unverified is shown as unverified and excluded from exports. The output is framed as issues for practitioner review, never as patentability conclusions, and the existing AI notice is shown. Tests: a fabricated section or quote is rejected.
4. **Office action review.** A workflow template: an uploaded office action (a matter document) goes through extraction (rejections, statute, claims and references, each quote-verified against the office action text), then MPEP retrieval per rejection basis, then a draft issue list, then an **approval step** by a named practitioner. Nothing is marked final before approval.
5. **Reports and approvals.** PDF and DOCX generation follows `contract_analysis/report.py`. A report includes only approved items, shows the verification status and revision of every citation, the reviewer and date, and the disclaimer. Each export is audited, and export and deletion events join the fail-closed audit list.

## Security and deletion

- Each route checks matter membership minus walls (existing). There are new permissions `patent.write` and `patent.approve` in `permissions.py`; the approver can't be the same person as the author of the approved version, unless an admin allows it.
- Database: all tenant tables are in `rls.py`, so the fence covers ad-hoc SQL too.
- Deletion: workspace rows cascade from the matter. Documents use the existing delete path, which respects legal hold and retention. Disclosure versions are deleted with the workspace, and deletion is audited.
- Audit `log_event` covers: workspace created and deleted, disclosure version saved, mapping verified, review decision, report exported.
- There are no new outbound destinations except the operator-run USPTO ingest and the user's configured AI provider.

## Not in scope until a release gate

Real client data, deadline computation, filing, public deployment, paid services, and production migrations.
