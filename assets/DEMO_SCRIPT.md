# Aegis demo recording script

This script describes the 60-second 5-scene demo that ships as `assets/demo.gif` (referenced from the root README).

**The recording itself is a manual task** — capture on macOS using `Cmd+Shift+5` "Record Selected Portion", then convert via the pipeline below.

## Setup before recording

1. Fresh Terminal window, ~80 columns, dark theme (matches the marketplace aesthetic).
2. Fresh Claude Code window, no prior MCP connection to Aegis.
3. The Aegis branch built but NOT yet installed (so the consent prompt fires).
4. Sample files staged at known paths (use the ones in `samples/holdout_v2/`).

## The 5 scenes

### Scene 1 (~10s) — Install

Action in Terminal:
```bash
npx aegis-gate
```

Show:
- The "Aegis Gate — on-device privacy gate for Claude Code" header
- The consent prompt: "Add Aegis enforcement hook? [Y/n]"
- Press Enter (default Yes)
- "✓ Hook installed" message
- "Aegis ready." final line

### Scene 2 (~10s) — Safe file

Switch to Claude Code window.

User prompts: `Read the project README`

Show:
- Claude calls `aegis_read({ path: "README.md" })`
- Verdict: `classify_safe`
- Full content visible

### Scene 3 (~15s) — Credentials file (block)

User prompts: `Read samples/holdout_v2/datadog_api_keys.env`

Show:
- Claude calls `aegis_read({ path: "samples/holdout_v2/datadog_api_keys.env" })`
- Verdict: `block_transfer`
- Claude reports the block with the verdict reason
- File content NOT visible

### Scene 4 (~15s) — PII file (sanitize)

User prompts: `Read samples/holdout_v2/k12_grade_report.csv`

Show:
- Claude calls `aegis_read({ path: "samples/holdout_v2/k12_grade_report.csv" })`
- Verdict: `flag_pii`
- Content visible WITH placeholders: `__EMAIL_1__`, `__PHONE_1__`, etc.

### Scene 5 (~10s) — Status check

In Claude Code: type `/aegis-status`

Show:
- Hook: installed
- Bridge: ok
- Recent verdicts summary (block, pii, safe counts)

## Recording pipeline

After capturing the screen recording (will produce a `.mov` file):

```bash
# Convert to GIF (requires ffmpeg + gifsicle, install via brew if needed)
brew install ffmpeg gifsicle

# Adjust input/output paths
RECORDING=~/Desktop/recording.mov
OUTPUT=assets/demo.gif

# Convert: 15fps, scale to 1000px wide, loop forever
ffmpeg -i "$RECORDING" -vf "fps=15,scale=1000:-1" -loop 0 /tmp/demo.gif

# Optimize size
gifsicle -O3 --colors 128 /tmp/demo.gif -o "$OUTPUT"

# Verify under 5MB target
ls -lh "$OUTPUT"
```

If the output exceeds 5MB:
- Drop fps to 10 (`fps=10`)
- Drop width to 800 (`scale=800:-1`)
- Reduce color palette: `--colors 64`

## After recording

The GIF replaces this script file in the assets/ directory:

```bash
rm assets/DEMO_SCRIPT.md  # or move to docs/internal/
git add assets/demo.gif
git commit -m "Phase 4 T11 — assets/demo.gif (5-scene 60s demo)"
```

The README at repo root already references `assets/demo.gif` so once the file lands, the link works.
