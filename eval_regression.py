"""Phase 3b.5 — ambiguity regression suite (10 hand-picked cases).

Includes the 5 known failures from Phase 3b's 98-sample eval + 5 nearby
tricky .example files that the current head gets right. Used informally
to verify no regression on cases we already understand. Not the headline
number; not gating.
"""
from __future__ import annotations

LABELS = ("classify_safe", "flag_pii", "block_transfer", "request_permission")

CASES: list[tuple[str, str]] = [
    # The 5 Phase 3b failures — these MUST be classified correctly under the new head
    # for the "zero fail-open" gate clause to hold (specifically owid).
    ("samples/external/flag_pii/delphix_dxtoolkit_f6fdab90.example", "flag_pii"),
    ("samples/external/flag_pii/AgrawalVi_ponovo_83908028.csv", "flag_pii"),
    ("samples/external/block_transfer/owid_owid-grapher_b8fa04ba.example-full", "block_transfer"),
    ("samples/hr_exit_interview_records.txt", "flag_pii"),
    ("samples/saas_help_center_article.md", "classify_safe"),

    # 5 nearby tricky .example files the current Phase 3b head gets RIGHT.
    # Must-not-regress: if a retrained head fails on any of these, flag in scorecard.
    ("samples/external/block_transfer/tambo-ai_tambo_4bac536a.example", "block_transfer"),
    ("samples/external/block_transfer/denysdovhan_smart-home_4c389a32.example", "block_transfer"),
    ("samples/external/block_transfer/melkor217_ayanami_23ae012e.example", "block_transfer"),
    ("samples/external/block_transfer/coneshare_coneshare-compose_37f0f89b.example", "block_transfer"),
    ("samples/external/block_transfer/MarekWo_UPS_monitor_a26577d7.example", "block_transfer"),
]
