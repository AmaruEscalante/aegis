# Aegis Roadmap

**Last updated:** 2026-05-18

This is the project-level roadmap — where Aegis has been, where it's going, and the explicit decisions we've parked for later phases. Specs and execution plans for each phase live in `docs/superpowers/`.

## Where we are

| Phase | Status | Summary |
|---|---|---|
| **Phase 0** | done | Hackathon build: Cactus + FunctionGemma stack. Working but FunctionGemma needed fine-tuning we never did. |
| **Phase 1** | done | Migrated to Ollama. Evaluated 4 base models on 12 hand-curated real samples. Result: `gemma4:31b` best at 91.67% / 30s; `embeddinggemma` fastest at 103 ms but only 75% with k-NN. Scorecard recommended training a classifier head on top of EmbeddingGemma. See [`docs/eval-results/scorecard.md`](eval-results/scorecard.md). |
| **Phase 2** | done | Trained a Logistic Regression head on 200 hand-curated examples × 768-dim EmbeddingGemma embeddings. 12/12 accuracy on the original 12-sample real eval at warm p50 = 98 ms. Head fits in 25 KB (`aegis-head/lr.joblib`). 5-fold CV macro-F1 on training set = 0.980. |
| **Phase 3a** | done | Expanded eval set 12 → 30 samples (11 hand-curated + 7 mined from public GitHub via `tools/sample_collector.py`). LR head: **29/30 (96.67%) / macro F1 0.967 / warm p50 104 ms.** gemma4:31b: **26/30 (86.67%) / macro F1 0.868 / warm p50 35 s.** **10-percentage-point gap (4× error-rate ratio) at ~335× lower latency** — Phase 1/2 statistical-tie caveat resolved. Merged to `main` in PR #2. |
| **Phase 3b** | done | Dropped the Ollama dependency from the bridge's default path. New `aegis/embedding.py` module wraps `sentence-transformers` and is shared by the bridge (via `LocalBackend`), training, and eval scripts. Eval set expanded 30 → 98 real samples. Trained head retrained with no-prompt embeddings (CV-selected `classify_doc` prompt failed held-out gate; rolled back). **93/98 = 94.90% on the held-out eval (Wilson CI [88.6%, 97.8%]).** Ollama backend remains reachable via `--backend ollama`. See `docs/superpowers/specs/2026-05-18-phase-3b-drop-ollama-design.md`. |

## Phase 3 — make the trained head shippable

The goal of Phase 3 is to turn "we have a trained head" into "Aegis is a self-contained, production-ready local privacy gate." Four pieces, roughly independent:

### 3a — Expand the eval set to 30 samples ✅ done (2026-05-17)

Expanded from 12 to 30 real samples using two channels: 11 hand-curated additions in `samples/` (Channel A) plus 7 mined from public GitHub repos via `tools/sample_collector.py` into `samples/external/` with provenance metadata (Channel C). Channel B (developer's own dev directories, anonymized) deferred for now — the 18 from A + C were enough to resolve the statistical tie.

Re-ran the two viable production candidates (skipped e2b, FunctionGemma, k-NN — eliminated in Phase 1 on architectural grounds). Trained LR head landed at **29/30 (96.67%) / macro F1 0.967 / warm p50 104 ms**, gemma4:31b at **26/30 (86.67%) / macro F1 0.868 / warm p50 35 s**. The head's one error is one gemma4:31b also makes (defensibly ambiguous mixed-signal file).

See [`docs/eval-results/scorecard.md`](eval-results/scorecard.md) for the full split-by-eval-set scorecard.

### 3b — Drop the Ollama dependency ✅ done (2026-05-18)

Replaced the Ollama HTTP backend with in-process inference via `sentence-transformers`. New `aegis/embedding.py` module owns the `Embedder` class, used by the bridge, `train/train_head.py`, and `train/eval_head.py`. Bridge gains a `--backend {local,ollama}` flag (default `local`); the Ollama path is preserved for dev / A/B comparison but is no longer required for normal use.

Eval set was expanded from 30 to 98 samples (Channels A + C) to give shipping decisions a defensible noise floor. The plan's bet on task-specific prompts ("Classify the following document: ") was tested via a 4-prompt CV sweep and selected as the winner by CV macro-F1 — but failed the held-out decision gate at 88/98. Rolled back to no-prompt (`TASK_PROMPT="none"`) and shipped at **93/98 = 94.90%** (Wilson 95% CI [88.6%, 97.8%]).

See [`docs/eval-results/scorecard.md`](eval-results/scorecard.md) for the full 98-sample row + Phase 3b outcome write-up, including the failed-prompt experiment and lessons learned.

### 3c — Wire `HeadBackend` into `aegis_bridge.py`

The bridge currently routes `/classify` through `OllamaBackend` (gemma4:31b). After Phase 3a confirms the win, switch the default to `HeadBackend` (loads `aegis-head/lr.joblib` at startup, embeds via the local sentence-transformers, predicts in-process).

**Keep `OllamaBackend` reachable via a flag** for A/B testing and as a heavy-weight fallback if the head ever underperforms in production.

### 3d — Add PDF + DOCX support to `aegis_read`

Today `aegis_read` only handles UTF-8 text. Extend it to also accept:
- **PDFs:** text extraction via `pypdf` or `pdfplumber`. Works for ~95% of PDFs (anything not a pure-image scan). Same downstream pipeline.
- **DOCX:** text extraction via `python-docx`. DOCX is structured XML internally; this is trivially easy.

Scanned-image PDFs are explicitly out of scope for Phase 3 — they require OCR (Tesseract or Apple Vision), which we'd add in Phase 5 alongside true image support.

## Phase 4 — publish as MCP marketplace plugin

The Aegis MCP server is already the right shape (`aegis_read`, `aegis_classify`, `aegis_policy_explain`, `aegis_sanitize_path`). Once Phase 3 lands, Aegis becomes a self-contained, pip-installable / npx-installable package.

**Deliverables:**
- `pyproject.toml` / `package.json` packaged for distribution; `pipx install aegis-mcp` or `npx aegis-mcp` works out of the box.
- README with a 30-second install demo and a screen recording showing the privacy gate in action (safe file → pass-through, credentials file → blocked, NDA → request permission).
- Listing in the Anthropic MCP directory and the Claude Code plugin marketplace.
- Privacy promise stated upfront: weights bundled, no network calls at inference time, no telemetry by default.

## Phase 5 — image support (deferred)

Three layered approaches, in order of effort:

1. **OCR-then-classify:** extract text from images via Tesseract (cross-platform) or Apple Vision (macOS, much higher quality). Pipe through the existing pipeline. Catches "screenshot of credentials file," misses "photo of a face."
2. **Vision embedder + new head:** train an analogous LR head on top of CLIP, SigLIP, or PaliGemma 2. Requires a labeled image training set (~200 images × 4 classes).
3. **Vision-language model directly:** use PaliGemma 2 as a generative classifier the way we used `gemma4:31b` for text in Phase 1. Slower but flexible.

Start with (1), escalate as needed.

## Data sourcing strategy

This applies to both **training set expansion** (currently 200 examples, may grow if Phase 5 needs vision data) and **eval set expansion** (currently 12, growing to 30 in Phase 3a).

We have three viable channels. Use them in combination.

### Channel A — hand-curate (we did this for the 200 training examples)

What we did in Phase 1/2. Highest quality control, deliberately diverse, no PII concerns (we wrote it). Fast for small batches. **Recommended starting point** for Phase 3a's 18 new eval files.

**Limitation:** the model only sees the kinds of files we can imagine. Real-world drift (multilingual content, unusual file shapes, near-boundary examples) is harder to catch this way.

### Channel B — your own dev directories (anonymized)

Walk through `~/dev`, `~/Documents`, `~/Downloads` for real files matching each verdict class. Real `.env` files, real CSVs from past projects, real meeting notes, real READMEs. Anonymize identifying details (find/replace names + emails + project codenames) before committing.

**Highest signal** of the three channels — these are unambiguously not synthetic. **Run them through `train/generate_dataset.py`'s validators** (regex PII / secret patterns) before committing to confirm no real secrets leaked through anonymization.

**Cost:** moderate, depends on how thorough the anonymization is.

### Channel C — public / online sources (first-class option)

This is the channel that scales. Three sub-paths:

**C1 — Public GitHub mining.** Use GitHub's code search to find real-shaped files in public repos:
- `path:*.env extension:env` → real env templates and committed dev configs
- `path:docker-compose.yml STRIPE_SECRET_KEY` → real prod-shaped configs (mostly placeholder values; perfect for `block_transfer`)
- `path:README.md` → effectively unlimited safe-class files
- `path:patients.csv` or `path:users.csv` in test/fixture dirs → synthetic-but-realistic PII

We can script the collection: `gh api` + filtering + dedup. Output goes into `samples/external/` with provenance metadata (source URL, license, commit SHA).

**C2 — Hugging Face datasets.** The community has curated public datasets that are directly useful for us:
- `ai4privacy/pii-masking-200k` — labeled PII data across languages
- `bigbio/cdr` — clinical record entity recognition (great `flag_pii` source)
- `nielsr/funsd` — scanned-form data with PII (useful when Phase 5 ships)
- `synthetic-pii/*` — multiple synthetic-PII generators with labels

We'd need to be careful about license terms before redistributing, but using these as one-time sources for our own curation is generally fine.

**C3 — Common Crawl & web corpora.** For `classify_safe` content (READMEs, marketing blogs, public docs), Common Crawl has effectively unlimited supply. Probably overkill for our scale; flag for later if we ever need tens of thousands of safe examples.

**Process for online-sourced files:**
1. Pull candidates into `samples/external/raw/` with provenance.
2. Run them through our validators (length, PII regex, secret regex) and discard anything that doesn't match the expected class signal.
3. Anonymize anything that looks like real PII (the public GitHub mining channel sometimes turns up actually-leaked real secrets that GitHub's scanner missed — handle with care, don't redistribute).
4. Promote vetted files to `samples/` proper with a `provenance: external` tag in the case metadata.

**Cost:** medium upfront tooling investment (~half a day to write a `tools/sample_collector.py`), then very cheap to run.

### Recommended mix for Phase 3a

- **8 files from Channel A** (hand-curate) — covers the edge cases we specifically want to test.
- **6 files from Channel B** (your dev dirs, anonymized) — high-signal real-world examples.
- **4 files from Channel C** (public mining) — pure real-world distribution, even at small scale.

That gets us to 30 total (12 original + 18 new), with provenance diversity across all three channels.

### Recommended mix for future training-set expansion

If we ever expand beyond 200 training examples (e.g., when Phase 5 ships and we need image data, or if a new class emerges), shift the mix toward Channel C — at scale, hand-curation gets expensive and Channel C is the only one that produces thousands of examples cheaply.

## What's explicitly out of scope (and why)

- **Fine-tuning EmbeddingGemma itself.** The frozen embedder + LR head architecture is working. Fine-tuning the encoder is expensive, risks losing the encoder's general representational quality, and won't help unless the failure mode is "embedder doesn't represent these distinctions well" — which Phase 2 evidence contradicts. Reserved as a "Phase X rescue path" only.
- **FunctionGemma LoRA fine-tune.** Same logic — was the Phase 1 rescue path, no longer needed.
- **Multi-model ensemble.** Could marginally boost accuracy by running both `HeadBackend` and `OllamaBackend` and voting, but the latency cost is dominated by `gemma4:31b` (30s), which kills the point. Reserved for "we need the last 2pp of accuracy and don't care about latency."
- **Cloud inference fallback.** Aegis is on-device-first by design. Adding a cloud fallback would invert the privacy story. Hard no.

## Open questions / decisions to make

- **MCP plugin name.** `aegis-mcp`? `aegis-privacy-gate`? `mcp-aegis`? Picks affect SEO in marketplace listings.
- **License.** MIT for max adoption? Apache 2.0 to keep patent grant explicit? Decide before Phase 4 publish.
- **Telemetry.** Default off (privacy promise). Optional opt-in usage stats? If yes, what backend (Honeycomb? PostHog? Self-hosted Plausible)? Decide before Phase 4.
- **Custom verdict classes.** Today the head is fixed at 4 classes. Should v2 of the head support user-defined classes (e.g., "internal-Anthropic-confidential")? If yes, that's a Phase 6+ feature.
