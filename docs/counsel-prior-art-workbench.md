# Prior art discovery workbench (preview)

Independent Counsel addition to CaseCite, Copyright 2026 Thomas Unise, Apache-2.0. Retain upstream LICENSE and NOTICE.md.

Based on the integrated PR #12 commit 77c8e20, which contains PR #11 (migration 028) and PR #8. Do not combine the alternative migrations from PR #9 or the parallel MPEP implementation in PR #10. Both remain historical draft candidates pending maintainer disposition. This branch adds no migrations and no provider credentials.

The IP Research workbench generates generic Boolean keyword ideas from manually entered fictional terms, lists fixed official discovery links, and lets a reviewer keep a local checklist and candidate reference notes. It does not automate searches, check dates, validate publication numbers, verify passages, provide a patentability opinion, or persist data. It sends no worksheet text to external sites or server, and exports only after an explicit fictional-data acknowledgment. The JSON file is unencrypted. Use no actual client information. Provider-specific query syntax is intentionally not generated.

Official entry points checked November 26, 2026:
- USPTO Patent Public Search: https://www.uspto.gov/patents/search/patent-public-search
- USPTO search strategy: https://www.uspto.gov/patents/search/patent-search-strategy
- USPTO classification search: https://www.uspto.gov/web/patents/classification/
- EPO Espacenet: https://www.epo.org/en/searching-for-patents/technical/espacenet
- WIPO PATENTSCOPE: https://www.wipo.int/en/web/patentscope/

The USPTO announced sign-in for Patent Public Search starting December 4, 2026: https://www.uspto.gov/about-us/news-updates/patent-public-search-require-registration-access-beginning-dec-4-2026

Next gates: verify real MPEP ingestion, integrate a single cited AI research pipeline against the stored section IDs/hashes in PR #12 (do not merge the alternate corpus implementation), then review terms/quotas/credential handling and confidentiality for an authorized live patent API. Add matter-scoped reference import and server-side source matching only after governance review. No production deployment or paid API calls.
