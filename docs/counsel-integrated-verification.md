# Counsel integration and Word verification

Independent Counsel addition to CaseCite, Copyright 2026 Thomas Unise, Apache-2.0. Retain LICENSE and NOTICE.md.

This draft branch includes the accumulated #8, #11, #12, #13, #14 and #15 work. It corrects the two Ruff format differences reported on PR #15. Do not merge the competing #9 and #10 implementations; they conflict with the preferred migration and corpus lineage. Review the single cumulative diff against main before any merge. All earlier branches are retained for review; none was merged or closed by this change.

Word changes are presentation only. The existing device-code flow, API paths, command identifiers, storage keys, Word permissions, manifest GUID and upstream attribution stay unchanged. Manifest version is 0.1.1.0. For an independent deployment, assign a distinct WORD_ADDIN_ID and keep it stable across subsequent versions. Existing icon images are unchanged; replace them with the owner's actual original logo before release. The support link points at the fork repository, not an unmerged documentation URL. Current Word features are contract analysis, tracked changes and document research, not the new Patent Studio or patent-specific AI.

Verification gates:
1. All CI jobs on this exact branch tip must pass; do not assume the older green baseline covers this diff.
2. Start an isolated fictional-data instance. Verify sign-in, matter isolation, PDF/DOCX generation and MPEP ingestion against reviewed official source pages.
3. Verify add-in manifest rendering, HTTPS and CORS with the actual private deployment origin, then sideload in a supported Word host. Test device approval, sign-out, matter selection, research, tracked-change behavior and narrow pane layout. Never use real documents or a paid model for preview.
4. Integrate grounded AI against the stored MPEP corpus and implement human approval and remaining lifecycle checks. Manual prior art and Office Action notes are not integrated into the saved report; live prior art retrieval remains unimplemented.
5. Review security, original logo, notices, DCO, licensing and release requirements before merging or deploying. No deployment, paid services, production migration or Store submission is authorized by this PR.

The local runtime and real Word host were not available during this edit. Existing automated Word tests use mocks, not an actual Word host.
