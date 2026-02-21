// ============================================================================
// END-TO-END TESTS — Full Aegis middleware pipeline against real files
// ============================================================================
// Tests the COMPLETE middleware stack: aegis_read tool → router/classify.ts
// → aegis_bridge.py → LM Studio (summarize) → FunctionGemma (classify)
// → DataGuard sanitization (for flag_pii verdicts)
//
// Requires:
//   1. LM Studio running with smollm2-1.7b-instruct (port 1234)
//   2. Aegis bridge running:
//      uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
//
// Run with:
//   npx vitest run tests/e2e.test.ts

import { describe, it, expect, beforeAll } from "vitest";
import path from "path";
import type { DataGuardConfig, ClassifyResult } from "../src/types";
import { classifyFile, healthCheck } from "../src/router/classify";
import { createDataguardRead } from "../src/tools/dataguard_read";
import { createAegisClassify } from "../src/tools/aegis_classify";

const SAMPLES_DIR = path.resolve(__dirname, "../../samples");

const TEST_CONFIG: DataGuardConfig = {
  denyPathGlobs: ["**/.env", "**/.env.*", "**/*.pem", "**/.ssh/**"],
  allowedRoots: [path.resolve(__dirname, "../..")],
  sanitizeAlwaysGlobs: ["**/*.pdf", "**/*.docx"],
  maxFileBytes: 5 * 1024 * 1024,
  cacheDir: "/tmp/aegis-e2e-cache",
  auditLogPath: "/tmp/aegis-e2e-audit.jsonl",
  llmProvider: "ollama",
  llmMode: "prompt",
  ollamaBaseUrl: "http://127.0.0.1:11434",
  ollamaModel: "gemma2:latest",
  ollamaTimeoutMs: 30000,
  openrouterApiKey: "",
  openrouterModel: "qwen/qwen3-coder",
  openrouterTimeoutMs: 60000,
  aegisEnabled: true,
  aegisBridgeUrl: "http://127.0.0.1:7523",
  aegisBridgeTimeoutMs: 15000,
};

function readSample(name: string): string {
  const fs = require("fs");
  return fs.readFileSync(path.join(SAMPLES_DIR, name), "utf-8");
}

let bridgeAvailable = false;

beforeAll(async () => {
  const health = await healthCheck(TEST_CONFIG);
  bridgeAvailable = health.status === "ok";
  if (!bridgeAvailable) {
    console.warn(
      "\n[e2e] Aegis bridge not running — skipping e2e tests.\n" +
      "      Start it with: uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter\n"
    );
  } else {
    console.log(
      `[e2e] Bridge connected: backend=${health.backend}, model=${health.model}`
    );
  }
});

// ============================================================================
// SECTION 1: Pipeline mechanics — verify each route (safe/flag_pii/block/escalate)
// works end-to-end through the middleware, regardless of model accuracy
// ============================================================================

describe("e2e: pipeline mechanics (aegis_read tool)", () => {
  let aegisRead: ReturnType<typeof createDataguardRead>;

  beforeAll(() => {
    aegisRead = createDataguardRead(TEST_CONFIG);
  });

  it("classifies and returns a valid result for every sample file", async () => {
    if (!bridgeAvailable) return;
    const fs = require("fs");
    const files = fs.readdirSync(SAMPLES_DIR) as string[];

    const results: Array<{ file: string; verdict: string; method: string; redactions: number }> = [];

    for (const file of files) {
      const samplePath = path.join(SAMPLES_DIR, file);
      try {
        const result = await aegisRead({ path: samplePath });
        results.push({
          file,
          verdict: (result as any).aegis_verdict ?? "flag_pii",
          method: result.method,
          redactions: result.redaction_count,
        });
      } catch (err: any) {
        // Block verdicts throw — that's correct behavior
        if (err.message?.includes("blocked")) {
          results.push({ file, verdict: "block", method: "aegis-blocked", redactions: 0 });
        } else {
          throw err;
        }
      }
    }

    // Print summary table
    console.log("\n  ┌──────────────────────────────────┬────────────┬──────────────────┬──────────┐");
    console.log("  │ File                             │ Verdict    │ Method           │ Redacted │");
    console.log("  ├──────────────────────────────────┼────────────┼──────────────────┼──────────┤");
    for (const r of results) {
      console.log(
        `  │ ${r.file.padEnd(32)} │ ${r.verdict.padEnd(10)} │ ${r.method.padEnd(16)} │ ${String(r.redactions).padStart(8)} │`
      );
    }
    console.log("  └──────────────────────────────────┴────────────┴──────────────────┴──────────┘");

    // Verify every file got a valid result
    expect(results.length).toBe(files.length);
    for (const r of results) {
      expect(["safe", "flag_pii", "block", "escalate"]).toContain(r.verdict);
    }
  }, 600000);

  it("returns aegis-safe method for open-source README (no PII)", async () => {
    if (!bridgeAvailable) return;
    const result = await aegisRead({ path: path.join(SAMPLES_DIR, "open_source_readme.md") });
    console.log(`  open_source_readme.md => method=${result.method}`);
    // The model consistently classifies this as safe
    expect(result.method).toBe("aegis-safe");
    expect(result.redaction_count).toBe(0);
  }, 30000);

  it("returns content in summary mode (truncated to 2000 chars)", async () => {
    if (!bridgeAvailable) return;
    const result = await aegisRead({ path: path.join(SAMPLES_DIR, "blog_post_draft.txt"), mode: "summary" });
    if ("sanitized_text" in result) {
      expect((result as any).sanitized_text.length).toBeLessThanOrEqual(2000);
      console.log(`  blog_post_draft.txt (summary) => ${(result as any).sanitized_text.length} chars`);
    }
  }, 30000);
});

// ============================================================================
// SECTION 2: Router classification — all 12 files through the bridge
// ============================================================================

describe("e2e: Aegis classification (all sample files)", () => {
  it("classifies all sample files and reports results", async () => {
    if (!bridgeAvailable) return;
    const fs = require("fs");
    const files = (fs.readdirSync(SAMPLES_DIR) as string[]).sort();

    const results: Array<{ file: string; verdict: string; confidence: number; time_ms: number }> = [];

    for (const file of files) {
      const text = readSample(file);
      const result = await classifyFile(text, TEST_CONFIG);
      results.push({
        file,
        verdict: result.verdict,
        confidence: result.confidence,
        time_ms: result.time_ms,
      });
    }

    // Print batch summary
    console.log("\n  ┌──────────────────────────────────┬────────────┬──────────┬──────────┐");
    console.log("  │ File                             │ Verdict    │ Confid.  │ Time     │");
    console.log("  ├──────────────────────────────────┼────────────┼──────────┼──────────┤");
    for (const r of results) {
      console.log(
        `  │ ${r.file.padEnd(32)} │ ${r.verdict.padEnd(10)} │ ${r.confidence.toFixed(2).padStart(8)} │ ${(r.time_ms.toFixed(0) + "ms").padStart(8)} │`
      );
    }
    console.log("  └──────────────────────────────────┴────────────┴──────────┴──────────┘");

    const verdictCounts = { safe: 0, flag_pii: 0, block: 0, escalate: 0 };
    for (const r of results) {
      verdictCounts[r.verdict as keyof typeof verdictCounts]++;
    }
    console.log(`\n  Total: ${results.length} files`);
    console.log(`  Safe: ${verdictCounts.safe}  Sanitize: ${verdictCounts.flag_pii}  Blocked: ${verdictCounts.block}  Escalate: ${verdictCounts.escalate}`);

    // Every file should get a valid verdict
    for (const r of results) {
      expect(["safe", "flag_pii", "block", "escalate"]).toContain(r.verdict);
    }
  }, 600000);
});

// ============================================================================
// SECTION 3: aegis_classify tool (standalone classification)
// ============================================================================

describe("e2e: aegis_classify tool", () => {
  let aegisClassify: ReturnType<typeof createAegisClassify>;

  beforeAll(() => {
    aegisClassify = createAegisClassify(TEST_CONFIG);
  });

  it("returns valid ClassifyResult for each sample file", async () => {
    if (!bridgeAvailable) return;
    const fs = require("fs");
    const files = (fs.readdirSync(SAMPLES_DIR) as string[]).sort();

    for (const file of files) {
      const result = await aegisClassify({ path: path.join(SAMPLES_DIR, file) });
      console.log(`  [aegis_classify] ${file} => ${result.verdict} (${result.confidence.toFixed(2)})`);
      expect(["safe", "flag_pii", "block", "escalate"]).toContain(result.verdict);
      expect(result.confidence).toBeGreaterThanOrEqual(0);
      expect(result.time_ms).toBeGreaterThanOrEqual(0);
    }
  }, 600000);
});
