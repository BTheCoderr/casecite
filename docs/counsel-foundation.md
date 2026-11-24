# SmartProBono Counsel — foundation and release gates

Status: development only; not approved for confidential client documents or production.

## Upstream provenance
- Upstream: https://github.com/thomasunise/casecite
- Baseline revision: bf235d45389a30670c32a12fcdfbd32204ca814e
- Upstream copyright: Copyright 2026 Thomas Unise.
- Preserve the upstream LICENSE (Apache-2.0), NOTICE.md and applicable third-party notices and file headers; clearly identify modified files as required. Do not imply upstream endorsement or use upstream trademarks as our own. Review separately licensed assets and dependencies before redistribution.
- Earlier CaseCite releases through 1.3.0 were distributed under Elastic License 2.0 according to the upstream README. Do not import earlier-only code without verifying its licensing.
- SmartProBono Counsel is a working product name, subject to clearance. It is an independent project; no Legora source, branding, confidential information or assets are used.

## Product direction
An affordable, self-hostable legal workspace, initially for US intellectual property practitioners. Preserve upstream document search, review tables, drafting, matter permissions and audit functionality while validating them independently. Start with fictional documents and publicly available legal sources. The community edition is intended to be open source; managed hosting and services are prospective commercial offerings, not yet available.

## Architecture and deployment
Keep the existing Vite/React frontend and FastAPI backend, PostgreSQL, Redis and local ChromaDB initially. Use upstream Docker Compose deployment instructions. Do not connect existing SmartProBonoIP databases, credentials, storage, or production deployments. Use a separate environment, secrets, and synthetic dataset. No infrastructure spending, public deployment, production migrations, or real client documents during foundation work.

## Phase gates
1. Foundation: preserve provenance and license; record upstream revision; independently validate dependency licenses, vulnerabilities and CI. Enable Actions on the fork if necessary; avoid privileged CI and unintended package publication.
2. Branding: use original Counsel visual assets, update product UI and metadata without changing upstream attribution or claiming affiliation; check trademark clearance before launch.
3. Runtime: build locally, run backend and frontend tests, migration tests against PostgreSQL, verify health endpoint, login, MFA, document upload/search/deletion, review tables, and backup/restore. Test with fictional data only.
4. Security: independently test cross-user/matter isolation (including RLS, vector queries, exports, jobs and cached data), session invalidation, least privilege, audit integrity, malicious files, SSRF and document prompt injection. Require explicit AI provider/data-flow settings, no undisclosed outbound document transfer, secure cookies/TLS and encrypted volumes/backups. Document provider retention and subprocessors; disable optional connectors until reviewed.
5. IP research: start with official USPTO MPEP sources, section/version metadata and verifiable source links; no invented citations or unsupported legal conclusions. Add fictional invention disclosure analysis and claim-element review with human approval. Distinguish educational information from legal advice.
6. Pilot: obtain attorney reviewer consent, complete confidentiality and data governance review, verify deletion and incident response, and resolve high-severity findings before any real data or public deployment.

## Definition of done for the foundation PR
- Baseline SHA and attribution documented.
- No runtime, secrets, infrastructure or upstream license changes.
- No confidential documents included.
- Fork checks explicitly reported as passed, failed or not run; upstream results are not fork validation.

## Outstanding verification
The upstream source contains a Dockerfile, lockfiles, security policy and tests for tenant isolation, RLS, encryption, authentication and audit integrity. Their presence is not evidence that the fork passes them. Independently execute CI and local runtime checks before accepting production readiness. In particular, the upstream documentation warns some data on volumes is stored in cleartext unless host disk encryption is configured, and external AI features can transmit document content to providers.
