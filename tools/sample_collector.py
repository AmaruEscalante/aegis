"""
Public-GitHub eval-sample collector (Channel C in the roadmap data-sourcing plan).

Searches public repos for files matching per-class patterns, fetches the
content via the git/blobs API, runs class-appropriate validators, and writes
vetted files to samples/external/<class>/ with a sibling .provenance.json.

Usage:
    .venv/bin/python tools/sample_collector.py classify_safe --max 2
    .venv/bin/python tools/sample_collector.py flag_pii      --max 2
    .venv/bin/python tools/sample_collector.py block_transfer --max 2
    .venv/bin/python tools/sample_collector.py request_permission --max 1

Requires:
    - gh CLI authenticated (`gh auth status`).
    - At least `repo` scope for code search.

Notes:
    - The collector is best-effort. Some classes (request_permission especially)
      are hard to source meaningfully from public repos because the entire
      class is "internal documents not normally public." For those, prefer
      Channel A (hand-curate) and use this tool only opportunistically.
    - Every collected file is logged with full provenance (repo, path, blob
      SHA, source URL) so the eval set is reproducible.
    - Files are run through a guardrail check to make sure we don't accidentally
      collect a real leaked secret (high-entropy random AWS/Stripe/etc tokens);
      anything that trips the guardrail is rejected with a warning.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

# ── Per-class search strategies ─────────────────────────────────────
# Each entry: list of (query_terms, extra_flags). Tried in order until --max collected.
QUERIES: dict[str, list[tuple[list[str], list[str]]]] = {
    "classify_safe": [
        (["##", "Installation"], ["--filename=README.md", "--limit=20"]),
        (["##", "Quick", "Start"], ["--filename=README.md", "--limit=20"]),
        (["##", "Unreleased"], ["--filename=CHANGELOG.md", "--limit=20"]),
    ],
    "flag_pii": [
        (["email", "phone"],   ["--filename=users.csv", "--limit=20"]),
        (["email", "address"], ["--filename=customers.csv", "--limit=20"]),
        (["email", "phone"],   ["--filename=contacts.csv", "--limit=20"]),
    ],
    "block_transfer": [
        (["SECRET", "TOKEN"],   ["--filename=.env.example", "--limit=20"]),
        (["DATABASE_URL"],      ["--filename=.env.sample",  "--limit=20"]),
        (["private_key_id"],    ["--extension=json", "--limit=20"]),
    ],
    "request_permission": [
        # Public CONFIDENTIAL-tone documents are rare. The "CONFIDENTIAL" keyword
        # produces too many false positives (security blog posts ABOUT confidential
        # info, rather than confidential documents themselves), so we lean on
        # structural NDA-template phrasing instead.
        (["non-disclosure", "agreement", "parties"], ["--extension=md", "--limit=20"]),
        (["WITNESSETH", "WHEREAS"], ["--extension=md", "--limit=20"]),
    ],
}

# ── Guardrails (do NOT collect real secrets) ────────────────────────
# Reject files that contain real-format AWS/Stripe-live/GH-PAT/etc patterns
# that aren't on a known-test allowlist. (Same logic that bit us during the
# Phase 2 push-protection incident.)
REAL_SECRET_PATTERNS = [
    # AWS keys NOT matching docs canonical examples
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), {"AKIAIOSFODNN7EXAMPLE", "AKIAI44QH8DHBEXAMPLE"}),
    # Stripe live keys (we never want any of these — only test keys are OK)
    (re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b"), set()),
    (re.compile(r"\brk_live_[A-Za-z0-9]{20,}\b"), set()),
    # GitHub PATs with high-entropy bodies (low-entropy placeholders are common in .env.example)
    (re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"), set()),
]

def has_real_secret(text: str) -> tuple[bool, str]:
    """Return (True, reason) if the text contains a real-looking secret not on the allowlist."""
    for pat, allowed in REAL_SECRET_PATTERNS:
        m = pat.search(text)
        if m and m.group() not in allowed:
            # If the matched body is mostly repeated chars or "EXAMPLE"/"XXX", it's fake.
            body = m.group()
            if "EXAMPLE" in body or "PLACEHOLDER" in body:
                continue
            if len(set(body)) <= 6:  # very low character variety → low entropy
                continue
            return True, f"matches {pat.pattern} → {body[:40]}"
    return False, ""


# ── Class-specific signal validators ─────────────────────────────────
def matches_class_signal(text: str, label: str) -> tuple[bool, str]:
    """Return (True, '') if text plausibly belongs to `label`, else (False, reason)."""
    if len(text) < 200:
        return False, f"too short ({len(text)} chars)"
    if len(text) > 8000:
        return False, f"too long ({len(text)} chars) — exceeds MAX_INPUT_CHARS"
    if label == "flag_pii":
        if not re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
            return False, "no email-shaped tokens"
    if label == "block_transfer":
        if not re.search(r"(?i)(secret|api[_-]?key|token|password|private[_-]?key)\s*[:=]", text):
            return False, "no credential-shaped key=value lines"
    # classify_safe and request_permission rely on document-level context, not regex.
    return True, ""


# ── gh CLI wrappers ──────────────────────────────────────────────────
def gh_search(query_terms: list[str], extra_flags: list[str]) -> list[dict]:
    cmd = ["gh", "search", "code", *query_terms, *extra_flags,
           "--json", "path,repository,sha,url"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  gh search failed: {result.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def gh_fetch_blob(owner_repo: str, blob_sha: str) -> str | None:
    """Fetch raw file content via the git/blobs API. Returns decoded text or None."""
    result = subprocess.run(
        ["gh", "api", f"repos/{owner_repo}/git/blobs/{blob_sha}",
         "-q", ".content"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    b64 = result.stdout.strip().replace("\n", "")
    try:
        return base64.b64decode(b64).decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


# ── Main collection loop ─────────────────────────────────────────────
def collect(label: str, max_count: int) -> list[pathlib.Path]:
    out_dir = pathlib.Path("samples/external") / label
    out_dir.mkdir(parents=True, exist_ok=True)
    collected: list[pathlib.Path] = []

    for query_terms, extra_flags in QUERIES[label]:
        if len(collected) >= max_count:
            break
        print(f"  query: terms={query_terms} flags={extra_flags}")
        hits = gh_search(query_terms, extra_flags)
        print(f"    -> {len(hits)} hits returned by gh search")

        for hit in hits:
            if len(collected) >= max_count:
                break
            owner_repo = hit["repository"]["nameWithOwner"]
            path = hit["path"]
            blob_sha = hit["sha"]
            source_url = hit["url"]

            text = gh_fetch_blob(owner_repo, blob_sha)
            if text is None:
                continue

            # Guardrail: never store a real-looking secret.
            real, reason = has_real_secret(text)
            if real:
                print(f"    SKIP {owner_repo}:{path} — guardrail: {reason}")
                continue

            ok, reason = matches_class_signal(text, label)
            if not ok:
                continue

            # Save with provenance
            content_hash = hashlib.sha1(text.encode()).hexdigest()[:8]
            ext = pathlib.Path(path).suffix or ".txt"
            safe_owner = owner_repo.replace("/", "_")
            out_path = out_dir / f"{safe_owner}_{content_hash}{ext}"
            out_path.write_text(text)

            provenance = {
                "label": label,
                "source_repo": owner_repo,
                "source_path": path,
                "source_blob_sha": blob_sha,
                "source_url": source_url,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "length_chars": len(text),
                "collector_query_terms": query_terms,
                "collector_extra_flags": extra_flags,
            }
            prov_path = out_path.with_name(out_path.name + ".provenance.json")
            prov_path.write_text(json.dumps(provenance, indent=2) + "\n")
            collected.append(out_path)
            print(f"    +  {out_path.name}  ({len(text)} chars, from {owner_repo})")

    return collected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("label", choices=list(QUERIES.keys()))
    ap.add_argument("--max", type=int, default=2)
    args = ap.parse_args()

    print(f"Collecting up to {args.max} samples for label={args.label}")
    collected = collect(args.label, args.max)
    print(f"\nCollected {len(collected)} files for {args.label}:")
    for p in collected:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
