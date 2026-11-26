# Counsel MPEP research preview

Independent Counsel addition to CaseCite (Copyright 2026 Thomas Unise, Apache-2.0). Preserve upstream LICENSE and NOTICE.md.

This is a bounded page-level public-source index, not a complete MPEP database, a current-law determination, a prior-art search engine, or an AI answer generator. The first eight pages are the existing directory's MPEP page IDs. No patent workspace or tenant index is queried. No production flags, migrations or deployment.

From a disposable development checkout with the backend dependencies installed, use:

```sh
mkdir -p backend/data/mpep
PYTHONPATH=backend python scripts/ingest_mpep.py --edition-label 'operator-confirmed revision' --output backend/data/mpep/reviewed-capture.json
```

Replace the example revision label with the actual edition/revision confirmed against the official index. The script accepts no arbitrary URL, refuses redirects, caps page size, records fetch timestamps and hashes, and never overwrites an existing output. It extracts normalized block text after a matching page heading. Review every page for missing text, subsection boundaries, revision labels, navigation artifacts and incorrect extraction BEFORE configuring the server. Never use synthetic fixtures as real corpus content. No corpus is bundled or automatically downloaded. Keep captured revisions separate; don't commit downloads to the repo.

Set MPEP_PREVIEW_CORPUS to the reviewed JSON file's absolute path inside the development backend, DEBUG=true, and VITE_MPEP_PREVIEW_ENABLED=true in the Vite dev frontend. The server endpoints remain disabled in production. The app must have read access, not write access, to the reviewed corpus. The user must have tools.research. Queries are explicit POST requests, not sent to the USPTO or AI providers. Do not enter confidential queries. Only exact excerpts from the stored text are returned; offsets refer to normalized indexed text, not HTML coordinates. The verification endpoint checks section, exact capture hash and quote; this is text matching, NOT verification of legal interpretation, currency or source authenticity. The source hash is not a digital signature. Page titles and capture time are not proof that subsequent law has not changed. The existing official directory remains available.

Before release: exercise the real importer against every official page, check extraction against source, add HTTP authorization and mobile/browser tests, confirm logging redaction, expand section-level indexing and version controls, and independently verify current law. No real client data, no filing, no legal conclusions.
