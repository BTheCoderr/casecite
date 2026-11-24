# IP research: phase one

Adds a local searchable directory of ten official USPTO references in the authenticated workspace. The directory searches only curated titles, section IDs and keywords. No external API, model call, full-text ingestion, retrieval-augmented generation or automated legal conclusions are implemented. Search input is not sent to a server by this view. Links use fixed official HTTPS destinations and noreferrer.

Source baseline verified 2026-11-24: https://www.uspto.gov/web/offices/pac/mpep/index.html (Ninth Edition Revision 01.2024, November 2024 publication). Individual section revision dates and later guidance may differ. Review subsequent publications and consolidated rules via the index. The source links are recorded in frontend/src/constants/ipSources.ts. Do not treat catalog keywords as legal assertions.

Next phase: versioned official-source ingestion, section-level citations, applicable-date filtering, verification against updated guidance and tests with fictional facts before any AI answers. No deployment or real client data.

Changes are independent Counsel additions to CaseCite (Copyright 2026 Thomas Unise, Apache-2.0). Preserve LICENSE and NOTICE.md.
