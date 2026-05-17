import { describe, it, expect, beforeAll, afterAll } from "vitest";
import http from "http";
import type { DataGuardConfig } from "../src/types";
import { classifyFile, healthCheck } from "../src/router/classify";

// ---- Mock bridge server ----

let mockServer: http.Server;
let mockPort: number;
let mockClassifyResponse: Record<string, unknown> = {};
let lastClassifyRequestBody: Record<string, unknown> | null = null;

function startMockBridge(): Promise<number> {
  return new Promise((resolve) => {
    mockServer = http.createServer((req, res) => {
      let body = "";
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        res.setHeader("Content-Type", "application/json");

        if (req.url === "/health") {
          res.end(JSON.stringify({ status: "ok", backend: "ollama", model: "gemma4:31b" }));
        } else if (req.url === "/classify") {
          lastClassifyRequestBody = body ? JSON.parse(body) : null;
          res.end(JSON.stringify(mockClassifyResponse));
        } else {
          res.statusCode = 404;
          res.end(JSON.stringify({ error: "not found" }));
        }
      });
    });

    mockServer.listen(0, "127.0.0.1", () => {
      const addr = mockServer.address();
      if (addr && typeof addr !== "string") resolve(addr.port);
    });
  });
}

function makeConfig(port: number): DataGuardConfig {
  return {
    denyPathGlobs: [],
    allowedRoots: [process.cwd()],
    sanitizeAlwaysGlobs: [],
    maxFileBytes: 5 * 1024 * 1024,
    cacheDir: "/tmp/aegis-test-cache",
    auditLogPath: "/tmp/aegis-test-audit.jsonl",
    llmProvider: "ollama",
    llmMode: "prompt",
    ollamaBaseUrl: "http://127.0.0.1:11434",
    ollamaModel: "gemma2:latest",
    ollamaTimeoutMs: 30000,
    openrouterApiKey: "",
    openrouterModel: "qwen/qwen3-coder",
    openrouterTimeoutMs: 60000,
    aegisEnabled: true,
    aegisBridgeUrl: `http://127.0.0.1:${port}`,
    aegisBridgeTimeoutMs: 5000,
  };
}

beforeAll(async () => {
  mockPort = await startMockBridge();
});

afterAll(() => {
  mockServer?.close();
});

// ---- Tests ----

describe("router/classify", () => {
  describe("classifyFile()", () => {
    it("returns safe verdict for classify_safe response", async () => {
      mockClassifyResponse = {
        tool: "classify_safe",
        arguments: { reason: "no sensitive data" },
        confidence: 0.95,
        time_ms: 30,
      };

      const result = await classifyFile("Some safe text", makeConfig(mockPort));
      expect(result.verdict).toBe("safe");
      expect(result.confidence).toBe(0.95);
      expect(result.reason).toBe("no sensitive data");
      expect(result.time_ms).toBe(30);
    });

    it("returns flag_pii verdict with pii_types", async () => {
      mockClassifyResponse = {
        tool: "flag_pii",
        arguments: { types: "email,ssn" },
        confidence: 0.88,
        time_ms: 25,
      };

      const result = await classifyFile("alice@example.com 123-45-6789", makeConfig(mockPort));
      expect(result.verdict).toBe("flag_pii");
      expect(result.pii_types).toBe("email,ssn");
      expect(result.confidence).toBe(0.88);
    });

    it("returns block verdict for block_transfer response", async () => {
      mockClassifyResponse = {
        tool: "block_transfer",
        arguments: { reason: "contains production API keys" },
        confidence: 0.99,
        time_ms: 20,
      };

      const result = await classifyFile("sk-live-abc123...", makeConfig(mockPort));
      expect(result.verdict).toBe("block");
      expect(result.reason).toBe("contains production API keys");
    });

    it("returns escalate verdict for request_permission response", async () => {
      mockClassifyResponse = {
        tool: "request_permission",
        arguments: { reason: "contains confidential financial data" },
        confidence: 0.72,
        time_ms: 35,
      };

      const result = await classifyFile("Q3 revenue: $2.4M...", makeConfig(mockPort));
      expect(result.verdict).toBe("escalate");
      expect(result.reason).toBe("contains confidential financial data");
    });

    it("sends raw text in classify request body", async () => {
      mockClassifyResponse = {
        tool: "classify_safe",
        arguments: { reason: "test" },
        confidence: 0.9,
        time_ms: 10,
      };
      lastClassifyRequestBody = null;

      await classifyFile("hello world", makeConfig(mockPort));
      expect(lastClassifyRequestBody).toEqual({ text: "hello world" });
    });

    it("falls back to flag_pii when bridge is unreachable", async () => {
      const config = makeConfig(19999); // port with no server
      const result = await classifyFile("Some text", config);

      expect(result.verdict).toBe("flag_pii");
      expect(result.confidence).toBe(0);
      expect(result.reason).toContain("Bridge unavailable");
    });

    it("falls back to flag_pii when bridge returns unknown tool", async () => {
      mockClassifyResponse = {
        tool: "unknown_tool",
        arguments: {},
        confidence: 0.5,
        time_ms: 10,
      };

      const result = await classifyFile("Some text", makeConfig(mockPort));
      expect(result.verdict).toBe("flag_pii");
    });
  });

  describe("healthCheck()", () => {
    it("returns ok when bridge is reachable", async () => {
      const health = await healthCheck(makeConfig(mockPort));
      expect(health.status).toBe("ok");
      expect(health.backend).toBe("ollama");
      expect(health.model).toBe("gemma4:31b");
    });

    it("returns unreachable when bridge is down", async () => {
      const health = await healthCheck(makeConfig(19999));
      expect(health.status).toBe("unreachable");
    });
  });
});
