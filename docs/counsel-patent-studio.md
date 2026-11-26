# Patent Analysis Studio — first vertical workflow

Independent Counsel addition to CaseCite (Copyright 2026 Thomas Unise, Apache-2.0). Preserve LICENSE and NOTICE.md.

This authenticated route provides a working manual worksheet: structured disclosure, potential contributor notes, office-action issues, claim-element rows with pinpoint disclosure support and candidate prior-art references, manual evidence statuses, missing-documentation questions and JSON export. It does not perform patent searching, AI analysis, source verification, legal conclusions, filing, deadline computation or matter persistence. A possible gap is a user-entered review status, not a machine finding.

Development use only with fictional data. Inputs are held in component memory and discarded on navigation or refresh; the module sends no inputs to an API or AI service and uses no localStorage. Exports are unencrypted and explicitly gated by a fictional-data acknowledgement. Review application-level logging, browser extensions, and provider/data handling before allowing real data. No production release approved.

Tests cover route auth, documentation prompts, mapping preservation, row controls and export acknowledgement. Remaining work: run CI and browser smoke, verified/versioned MPEP ingestion, matter-scoped persistence with existing permission and audit controls, multi-reference comparison, reviewer approval records, professional DOCX/PDF export, and only then evaluate AI-assisted extraction with verified pinpoint citations and human review.
