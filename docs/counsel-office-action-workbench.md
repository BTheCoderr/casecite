# Office Action review workbench

Independent Counsel addition to CaseCite, Copyright 2026 Thomas Unise, Apache-2.0. Preserve upstream LICENSE and NOTICE.md.

This local-only fictional-data prototype lives in IP Research, deliberately separate from persistent matter data. It detects literal claim mentions and explicit 35 USC sections 101, 102, 103 and 112 with bounded regular expressions. It preserves the source substring and context with UTF-16 offsets, never infers that a citation is a rejection, does not parse all Office Action layouts or associate particular claims with grounds, and never calculates deadlines. Unsupported references and unlabeled grounds can be missed. The existing official directory supplies a small set of non-exhaustive research links, not a legal mapping or a current-law check.

The reviewer may record examiner rationale, citations, evidence gaps and review notes. Status is manual and never approved. Editing the pasted source clears all local annotations. The checklist does not establish completion or correctness. Export is gated by an explicit fictional-data acknowledgment and contains unencrypted excerpts, notes and offsets, not the full pasted text. No AI, network call, browser persistence, server write, production migration or filing.

Next gates: integrate the versioned stored MPEP sections and actual matter-scoped source documents; add server-side quote checks and hash-bound practitioner review; use a separate approval workflow for any response draft. Confirm deadlines independently. No real client data until security and release review.

Based on PR #13 with its TypeScript test correction (c689d5c), which itself includes the green PR #12/11/8 lineage. Do not merge the competing #9/#10 migration/research implementations. CI and browser/runtime verification are still required.
