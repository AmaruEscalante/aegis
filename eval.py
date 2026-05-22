"""
Generalized eval runner for Aegis base models.

Runs one model through the eval set (12 hand-curated real samples in samples/),
reports per-class P/R/F1, accuracy, macro F1, confusion matrix, and warm-call
latency p50/p95/p99 (cold-start reported separately).

Supports two protocols:
  - bridge: POST to a running aegis_bridge.py /classify (generative models)
  - knn:    POST to Ollama /api/embed directly, k-NN against labeled set (embeddings)

Usage:
    # Generative model via bridge (bridge must already be running with --model <tag>)
    python eval.py --model gemma4:31b --protocol bridge

    # Embedding model directly (no bridge needed)
    python eval.py --model embeddinggemma --protocol knn

    # Auto-detect: if model name contains "embed", use knn; else bridge.
    python eval.py --model embeddinggemma   # -> knn
    python eval.py --model gemma4:e2b        # -> bridge

Output:
    docs/eval-results/<YYYY-MM-DD>-<model-tag>-base.txt
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# Optional numpy — only needed for the knn protocol. Import lazily.
def _import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        print("ERROR: numpy is required for --protocol knn. Run via `uv run python eval.py ...`.", file=sys.stderr)
        sys.exit(1)


# Hand-curated samples — Phase 1 original 12, plus 18 added in Phase 3a (eval
# expansion) for a 30-sample eval set. The 18 new samples are sourced from two
# channels described in docs/roadmap.md:
#   - Channel A (hand-curated by the project author): 11 files in samples/
#   - Channel C (mined from public GitHub via tools/sample_collector.py):
#     7 files under samples/external/, each with a sibling .provenance.json
CASES = [
    # ── Phase 1 originals (12) ────────────────────────────────────────────
    ("samples/open_source_readme.md",      "classify_safe"),
    ("samples/marketing_copy.txt",         "classify_safe"),
    ("samples/blog_post_draft.txt",        "classify_safe"),
    ("samples/patient_records.csv",        "flag_pii"),
    ("samples/employee_directory.json",    "flag_pii"),
    ("samples/user_database.json",         "flag_pii"),
    ("samples/api_config.env",             "block_transfer"),
    ("samples/kubernetes_secrets.yaml",    "block_transfer"),
    ("samples/docker_compose_prod.yml",    "block_transfer"),
    ("samples/vendor_evaluation.txt",      "request_permission"),
    ("samples/partnership_agreement.txt",  "request_permission"),
    ("samples/board_meeting_minutes.txt",  "request_permission"),

    # ── Phase 3a Channel A: hand-curated additions (11) ───────────────────
    ("samples/git_commit_message.txt",         "classify_safe"),
    ("samples/ci_build_log.txt",               "classify_safe"),
    ("samples/changelog_release_notes.md",     "classify_safe"),
    ("samples/sales_leads_export.csv",         "flag_pii"),
    ("samples/conference_attendees.json",      "flag_pii"),
    ("samples/donor_pledge_tracker.csv",       "flag_pii"),
    ("samples/openssh_private_key.pem",        "block_transfer"),
    ("samples/gcp_service_account_key.json",   "block_transfer"),
    ("samples/draft_press_release.txt",        "request_permission"),
    ("samples/internal_pricing_strategy.md",   "request_permission"),
    ("samples/layoff_communication_draft.md",  "request_permission"),

    # ── Phase 3a Channel C: mined from public GitHub (7) ──────────────────
    ("samples/external/classify_safe/ChainSafe_Delorean-Protocol_7aa4c1d5.md",      "classify_safe"),
    ("samples/external/classify_safe/tindy2013_stairspeedtest-reborn_145bd434.md",  "classify_safe"),
    ("samples/external/flag_pii/narismadz_O365PowerShell_ffc717d2.csv",             "flag_pii"),
    ("samples/external/flag_pii/delphix_dxtoolkit_f6fdab90.example",                "flag_pii"),
    ("samples/external/block_transfer/tambo-ai_tambo_4bac536a.example",             "block_transfer"),
    ("samples/external/block_transfer/fonoster_fonoster_fba18535.dev",              "block_transfer"),
    ("samples/external/request_permission/OperationCode_nda-agreement_truncated.md","request_permission"),

    # ── Phase 3b Channel C: mined from public GitHub (29) ─────────────────
    # classify_safe (8)
    ("samples/external/classify_safe/acsandmann_menuanywhere_38bb87f6.md",                 "classify_safe"),
    ("samples/external/classify_safe/Baachi_CouchDB_7cbd229d.md",                         "classify_safe"),
    ("samples/external/classify_safe/JudyYe_ghop_3d3051df.md",                            "classify_safe"),
    ("samples/external/classify_safe/cwru-courses_FALL2025ECSE390Team3_412b8bd1.md",       "classify_safe"),
    ("samples/external/classify_safe/rumblefrog_Source-Map-Thumbnails_94c09b7e.md",        "classify_safe"),
    ("samples/external/classify_safe/got-htf_pfm-front-end_d8b9aed9.md",                  "classify_safe"),
    ("samples/external/classify_safe/Sciencentistguy_rust-nix-shell_e7cf1cb7.md",         "classify_safe"),
    ("samples/external/classify_safe/WeijieMax_EyeReal_6b0dcfe2.md",                      "classify_safe"),
    # flag_pii (7 — microsoft template rejected as non-PII)
    ("samples/external/flag_pii/dittofeed_dittofeed_54edc973.csv",                        "flag_pii"),
    ("samples/external/flag_pii/burkeazbill_vroClientScripts_e0636b9e.csv",               "flag_pii"),
    ("samples/external/flag_pii/Macrometacorp_docs_1dfd86e4.csv",                         "flag_pii"),
    ("samples/external/flag_pii/jeeutai_ChessJaeguk_3b795b51.bak",                        "flag_pii"),
    ("samples/external/flag_pii/phanbaominh_PTUDW-17TN-Nhom13_e5f2c412.csv",             "flag_pii"),
    ("samples/external/flag_pii/AgrawalVi_ponovo_83908028.csv",                           "flag_pii"),
    # block_transfer (8)
    ("samples/external/block_transfer/FreekBes_improved_intra_server_15c05680.example",   "block_transfer"),
    ("samples/external/block_transfer/melkor217_ayanami_23ae012e.example",                "block_transfer"),
    ("samples/external/block_transfer/pulsarbot_Pulsar_bc903dec.example",                 "block_transfer"),
    ("samples/external/block_transfer/premieroctet_photoshot_8da808a3.example",           "block_transfer"),
    ("samples/external/block_transfer/owid_owid-grapher_b8fa04ba.example-full",           "block_transfer"),
    ("samples/external/block_transfer/MarekWo_UPS_monitor_a26577d7.example",              "block_transfer"),
    ("samples/external/block_transfer/denysdovhan_smart-home_4c389a32.example",           "block_transfer"),
    ("samples/external/block_transfer/coneshare_coneshare-compose_37f0f89b.example",      "block_transfer"),
    # request_permission (6 — github_dmca DMCA notice rejected as public filing)
    ("samples/external/request_permission/red-ant_au-non-disclosure_2c7cc125.md",         "request_permission"),
    ("samples/external/request_permission/fahyc_OpenOwnershipAgreementDraft_c74e0d21.md", "request_permission"),
    ("samples/external/request_permission/GAURAV30012001_MY-Repo_9b0f5035.md",            "request_permission"),
    ("samples/external/request_permission/sanddeveloper1-dev_heatseakerbackend_fe39b02d.md", "request_permission"),
    ("samples/external/request_permission/thooks1203_echodeed_3ea7c0df.md",               "request_permission"),
    ("samples/external/request_permission/cheshireterminal_Telegram-Trading-Bot_9def10b4.md", "request_permission"),

    # ── Phase 3b Channel A: hand-curated additions ─────────────────────────
    # classify_safe (10)
    ("samples/mit_license.txt",                   "classify_safe"),
    ("samples/apache_license.txt",                "classify_safe"),
    ("samples/rest_api_docs_snippet.md",          "classify_safe"),
    ("samples/python_tutorial_howto.md",          "classify_safe"),
    ("samples/stackoverflow_qa.txt",              "classify_safe"),
    ("samples/saas_help_center_article.md",       "classify_safe"),
    ("samples/conference_talk_abstract.txt",      "classify_safe"),
    ("samples/public_roadmap.md",                 "classify_safe"),
    ("samples/oss_contributor_onboarding.md",     "classify_safe"),
    ("samples/github_issue_bug_report.txt",       "classify_safe"),
    # flag_pii (10)
    ("samples/apartment_rental_application.txt",  "flag_pii"),
    ("samples/medical_lab_results.txt",           "flag_pii"),
    ("samples/loan_application_records.csv",      "flag_pii"),
    ("samples/hr_exit_interview_records.txt",     "flag_pii"),
    ("samples/customer_support_tickets_pii.csv",  "flag_pii"),
    ("samples/voter_registration_list.csv",       "flag_pii"),
    ("samples/insurance_claim_form.txt",          "flag_pii"),
    ("samples/hospital_discharge_summary.txt",    "flag_pii"),
    ("samples/dmv_registration_records.csv",      "flag_pii"),
    ("samples/wedding_rsvp_list.csv",             "flag_pii"),
    # block_transfer (9)
    ("samples/aws_credentials_dev.ini",           "block_transfer"),
    ("samples/npmrc_token_file",                  "block_transfer"),
    ("samples/pypirc_credentials.ini",            "block_transfer"),
    ("samples/tls_private_key.pem",               "block_transfer"),
    ("samples/ssh_config_with_keys",              "block_transfer"),
    ("samples/discord_webhook_config.env",        "block_transfer"),
    ("samples/postgres_pgpass_file",              "block_transfer"),
    ("samples/twilio_credentials.env",            "block_transfer"),
    ("samples/github_actions_secrets_export.env", "block_transfer"),
    # request_permission (11)
    ("samples/ma_term_sheet.md",                  "request_permission"),
    ("samples/internal_product_roadmap.md",       "request_permission"),
    ("samples/performance_review_document.txt",   "request_permission"),
    ("samples/salary_band_table.md",              "request_permission"),
    ("samples/trade_secret_formulation.txt",      "request_permission"),
    ("samples/strategic_competitor_analysis.md",  "request_permission"),
    ("samples/internal_audit_findings.md",        "request_permission"),
    ("samples/executive_offsite_agenda.md",       "request_permission"),
    ("samples/litigation_hold_notice.txt",        "request_permission"),
    ("samples/crisis_communications_playbook.md", "request_permission"),
    ("samples/investor_relations_talking_points.md", "request_permission"),
]

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

DEFAULT_BRIDGE_URL = "http://127.0.0.1:7523"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MAX_INPUT_CHARS = 8000


# ── Per-protocol classifiers ─────────────────────────────────────────────────

def classify_via_bridge(bridge_url: str, text: str) -> tuple[str, float, float]:
    """Return (predicted_tool, confidence, wall_ms)."""
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{bridge_url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    tool = data.get("tool", "request_permission")
    confidence = float(data.get("confidence", 0.0))
    return tool, confidence, wall_ms


def embed_text(ollama_url: str, model: str, text: str):
    """Call Ollama /api/embed and return (embedding_vector, wall_ms)."""
    payload = json.dumps({"model": model, "input": text[:MAX_INPUT_CHARS]}).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    np = _import_numpy()
    return np.array(data["embeddings"][0], dtype=np.float32), wall_ms


# ── Metrics ──────────────────────────────────────────────────────────────────

def f1_for_class(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def percentile(values: list[float], p: float) -> float:
    """p in [0, 100]. Returns NaN-like value (0.0) if values is empty."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


# ── Main ─────────────────────────────────────────────────────────────────────

def auto_protocol(model: str) -> str:
    """Heuristic: model names containing 'embed' use knn, otherwise bridge."""
    return "knn" if "embed" in model.lower() else "bridge"


def load_eval_texts() -> list[tuple[str, str, str]]:
    """Return [(path, label, text)] for every CASE. Skip missing files with a warning."""
    out = []
    for path, label in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
            out.append((path, label, text))
        except OSError as e:
            print(f"WARNING: skipping {path}: {e}", file=sys.stderr)
    return out


def main():
    parser = argparse.ArgumentParser(description="Aegis eval runner")
    parser.add_argument("--model", required=True, help="Ollama model tag (e.g., gemma4:e2b, embeddinggemma)")
    parser.add_argument(
        "--protocol",
        choices=["bridge", "knn", "auto"],
        default="auto",
        help="bridge = POST to running aegis_bridge.py /classify; knn = direct Ollama /api/embed + k-NN LOO-CV",
    )
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--warmup-calls",
        type=int,
        default=1,
        help="Throwaway calls before timing (default 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/eval-results"),
        help="Where to write the per-model log",
    )
    args = parser.parse_args()

    protocol = auto_protocol(args.model) if args.protocol == "auto" else args.protocol
    print(f"[eval] model={args.model} protocol={protocol}")

    cases = load_eval_texts()
    if len(cases) < 4:
        print(f"ERROR: only {len(cases)} eval cases loaded; need at least 4 (one per class).", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{date.today().isoformat()}-{args.model.replace(':', '-').replace('/', '-')}-base.txt"

    # ── Warm-up ──
    cold_start_ms = 0.0
    if args.warmup_calls > 0:
        warmup_text = cases[0][2]
        if protocol == "bridge":
            t0 = time.time()
            try:
                classify_via_bridge(args.bridge_url, warmup_text)
            except Exception as e:
                print(f"ERROR: bridge unreachable for warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        else:
            t0 = time.time()
            try:
                embed_text(args.ollama_url, args.model, warmup_text)
            except Exception as e:
                print(f"ERROR: Ollama embed failed during warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        for _ in range(args.warmup_calls - 1):
            if protocol == "bridge":
                classify_via_bridge(args.bridge_url, warmup_text)
            else:
                embed_text(args.ollama_url, args.model, warmup_text)
        print(f"[eval] warm-up done ({args.warmup_calls} call(s)), cold_start_ms={cold_start_ms:.0f}")

    # ── Eval loop ──
    rows = []  # (path, expected, predicted, confidence, latency_ms)
    warm_latencies = []

    if protocol == "bridge":
        for path, expected, text in cases:
            tool, confidence, wall_ms = classify_via_bridge(args.bridge_url, text)
            rows.append((path, expected, tool, confidence, wall_ms))
            warm_latencies.append(wall_ms)
            mark = "OK" if tool == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={tool:22s} ({wall_ms:.0f}ms)")
    else:  # knn
        np = _import_numpy()
        # Embed every case + measure latency for each
        embeddings = []
        for path, expected, text in cases:
            vec, wall_ms = embed_text(args.ollama_url, args.model, text)
            embeddings.append(vec)
            warm_latencies.append(wall_ms)
        X = np.stack(embeddings)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        Xn = X / np.clip(norms, 1e-12, None)
        sim = Xn @ Xn.T
        np.fill_diagonal(sim, -np.inf)
        for i, (path, expected, _text) in enumerate(cases):
            nbr = int(np.argmax(sim[i]))
            predicted = cases[nbr][1]
            confidence = float(sim[i, nbr])
            rows.append((path, expected, predicted, confidence, warm_latencies[i]))
            mark = "OK" if predicted == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={predicted:22s} sim={confidence:.2f} ({warm_latencies[i]:.0f}ms)")

    # ── Aggregate ──
    tp = {k: 0 for k in LABELS}
    fp = {k: 0 for k in LABELS}
    fn = {k: 0 for k in LABELS}
    correct = 0
    confusion = {k: {kk: 0 for kk in LABELS} for k in LABELS}
    for _path, expected, predicted, _conf, _ms in rows:
        if predicted in LABELS:
            confusion[expected][predicted] += 1
        if predicted == expected:
            correct += 1
            tp[expected] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1
    accuracy = correct / len(rows) if rows else 0.0
    macro_f1 = 0.0
    per_class = []
    for k in LABELS:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        per_class.append((k, p, r, f1))
        macro_f1 += f1
    macro_f1 /= len(LABELS)

    p50 = percentile(warm_latencies, 50)
    p95 = percentile(warm_latencies, 95)
    p99 = percentile(warm_latencies, 99)

    # ── Format the log file ──
    lines = []
    lines.append(f"Aegis base-model eval")
    lines.append(f"Date:     {date.today().isoformat()}")
    lines.append(f"Model:    {args.model}")
    lines.append(f"Protocol: {protocol}")
    lines.append(f"Cases:    {len(rows)}")
    lines.append(f"Warmup:   {args.warmup_calls} call(s); cold_start_ms={cold_start_ms:.0f}")
    lines.append("")
    lines.append(f"{'file':42s} {'expected':22s} {'predicted':22s} {'conf':>5s} {'ms':>7s}")
    lines.append("-" * 105)
    for path, expected, predicted, conf, ms in rows:
        mark = "OK" if predicted == expected else "XX"
        lines.append(f"{mark} {path:39s} {expected:22s} {predicted:22s} {conf:5.2f} {ms:7.0f}")
    lines.append("")
    lines.append(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    lines.append("-" * 50)
    for k, p, r, f1 in per_class:
        lines.append(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    lines.append("")
    lines.append("Confusion matrix (rows=expected, cols=predicted):")
    header = "             " + " ".join(f"{k[:10]:>10s}" for k in LABELS)
    lines.append(header)
    for row_label in LABELS:
        cells = " ".join(f"{confusion[row_label][col]:10d}" for col in LABELS)
        lines.append(f"{row_label:12s} {cells}")
    lines.append("")
    lines.append(f"Accuracy:                {accuracy:.2%} ({correct}/{len(rows)})")
    lines.append(f"Macro F1:                {macro_f1:.3f}")
    lines.append(f"Warm latency p50:        {p50:.0f} ms")
    lines.append(f"Warm latency p95:        {p95:.0f} ms")
    lines.append(f"Warm latency p99:        {p99:.0f} ms")
    lines.append(f"Cold start (1 throwaway): {cold_start_ms:.0f} ms")
    text = "\n".join(lines) + "\n"

    with out_path.open("w") as f:
        f.write(text)
    print()
    print(text)
    print(f"[eval] wrote {out_path}")
    sys.exit(0 if accuracy > 0.0 else 1)


if __name__ == "__main__":
    main()
