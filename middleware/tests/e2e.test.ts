// ============================================================================
// END-TO-END TESTS — Aegis router + DataGuard sanitization against real files
// ============================================================================
// These tests require the Aegis bridge server to be running:
//   uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
//
// Run with:
//   npx vitest run tests/e2e.test.ts
//
// Skip if bridge is not available (tests are conditional).

import { describe, it, expect, beforeAll } from "vitest";
import path from "path";
import type { DataGuardConfig } from "../src/types";
import { classifyFile, healthCheck } from "../src/router/classify";

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

/** Read a sample file's text content. */
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
    console.log(`[e2e] Bridge connected: backend=${health.backend}, model=${health.model}`);
  }
});

describe("e2e: Aegis classification", () => {

  // ---- Safe files should be classified as safe ----

  it("classifies marketing_copy.txt as safe", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("marketing_copy.txt");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  marketing_copy.txt => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("safe");
  });

  it("classifies open_source_readme.md as safe", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("open_source_readme.md");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  open_source_readme.md => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("safe");
  });

  it("classifies blog_post_draft.txt as safe", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("blog_post_draft.txt");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  blog_post_draft.txt => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("safe");
  });

  // ---- PII files should be flagged ----

  it("classifies patient_records.csv as flag_pii", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("patient_records.csv");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  patient_records.csv => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, pii_types=${result.pii_types}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("flag_pii");
  });

  it("classifies employee_directory.json as flag_pii", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("employee_directory.json");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  employee_directory.json => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, pii_types=${result.pii_types}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("flag_pii");
  });

  it("classifies user_database.json as flag_pii", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("user_database.json");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  user_database.json => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, pii_types=${result.pii_types}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("flag_pii");
  });

  // ---- Secrets files should be blocked ----

  it("classifies kubernetes_secrets.yaml as block", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("kubernetes_secrets.yaml");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  kubernetes_secrets.yaml => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("block");
  });

  it("classifies api_config.env as block", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("api_config.env");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  api_config.env => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("block");
  });

  it("classifies docker_compose_prod.yml as block", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("docker_compose_prod.yml");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  docker_compose_prod.yml => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("block");
  });

  // ---- Ambiguous files should escalate ----

  it("classifies board_meeting_minutes.txt as escalate", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("board_meeting_minutes.txt");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  board_meeting_minutes.txt => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("escalate");
  });

  it("classifies partnership_agreement.txt as escalate", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("partnership_agreement.txt");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  partnership_agreement.txt => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("escalate");
  });

  it("classifies vendor_evaluation.txt as escalate", async () => {
    if (!bridgeAvailable) return;
    const text = readSample("vendor_evaluation.txt");
    const result = await classifyFile(text, TEST_CONFIG);
    console.log(`  vendor_evaluation.txt => ${result.verdict} (confidence=${result.confidence.toFixed(2)}, ${result.time_ms.toFixed(0)}ms)`);
    expect(result.verdict).toBe("escalate");
  });
});
