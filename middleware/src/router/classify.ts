// ============================================================================
// AEGIS ROUTER — HTTP client for the FunctionGemma classification bridge
// ============================================================================
// Calls the Python aegis_bridge.py server over localhost to classify file
// content before deciding whether to sanitize, pass through, block, or escalate.

import http from "http";
import type { DataGuardConfig, ClassifyResult, BridgeHealth } from "../types";

// ---- Bridge verdict mapping ----

/** Map bridge tool names to Aegis verdicts. */
const VERDICT_MAP: Record<string, ClassifyResult["verdict"]> = {
  classify_safe: "safe",
  flag_pii: "flag_pii",
  block_transfer: "block",
  request_permission: "escalate",
};

// ---- HTTP helpers ----

/**
 * Send a JSON POST request to the bridge and return parsed response.
 * Uses Node's built-in http module (zero external dependencies).
 */
function postJson(
  baseUrl: string,
  path: string,
  body: Record<string, unknown>,
  timeoutMs: number
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const url = new URL(path, baseUrl);
    const payload = JSON.stringify(body);

    const req = http.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
        timeout: timeoutMs,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk: Buffer) => {
          data += chunk.toString("utf-8");
        });
        res.on("end", () => {
          try {
            resolve(JSON.parse(data) as Record<string, unknown>);
          } catch {
            reject(new Error(`Bridge returned non-JSON: ${data.slice(0, 200)}`));
          }
        });
      }
    );

    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`Bridge request timed out after ${timeoutMs}ms`));
    });

    req.on("error", (err) => {
      reject(new Error(`Bridge connection failed: ${err.message}`));
    });

    req.write(payload);
    req.end();
  });
}

/**
 * Send a GET request to the bridge and return parsed response.
 */
function getJson(
  baseUrl: string,
  path: string,
  timeoutMs: number
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const url = new URL(path, baseUrl);

    const req = http.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname,
        method: "GET",
        timeout: timeoutMs,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk: Buffer) => {
          data += chunk.toString("utf-8");
        });
        res.on("end", () => {
          try {
            resolve(JSON.parse(data) as Record<string, unknown>);
          } catch {
            reject(new Error(`Bridge returned non-JSON: ${data.slice(0, 200)}`));
          }
        });
      }
    );

    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Bridge health check timed out"));
    });

    req.on("error", (err) => {
      reject(new Error(`Bridge unreachable: ${err.message}`));
    });

    req.end();
  });
}

// ---- Public API ----

/**
 * Classify file content via the Aegis bridge (summarize + classify).
 *
 * Pipeline:
 *   1. POST /summarize  — sends first 8000 chars for on-device summarization
 *   2. POST /classify   — sends summary to FunctionGemma for classification
 *
 * On any failure (bridge down, timeout, malformed response) this function
 * degrades gracefully by returning verdict "flag_pii" — causing the caller
 * to fall through to the existing DataGuard sanitize-everything pipeline.
 */
export async function classifyFile(
  text: string,
  config: DataGuardConfig
): Promise<ClassifyResult> {
  const bridgeUrl = config.aegisBridgeUrl;
  const timeout = config.aegisBridgeTimeoutMs;

  try {
    // --- Step 1: Summarize ---
    const summarizeResp = await postJson(
      bridgeUrl,
      "/summarize",
      { text: text.slice(0, 8000) },
      timeout
    );
    const summary = (summarizeResp.summary as string) || text.slice(0, 2000);

    // --- Step 2: Classify ---
    const classifyResp = await postJson(
      bridgeUrl,
      "/classify",
      { summary },
      timeout
    );

    const toolName = classifyResp.tool as string;
    const args = classifyResp.arguments as Record<string, string> | undefined;
    const confidence = (classifyResp.confidence as number) ?? 0;
    const timeSummarize = (summarizeResp.time_ms as number) ?? 0;
    const timeClassify = (classifyResp.time_ms as number) ?? 0;

    const verdict = VERDICT_MAP[toolName] ?? "flag_pii";

    return {
      verdict,
      reason: args?.reason ?? args?.types ?? `classified as ${toolName}`,
      confidence,
      pii_types: verdict === "flag_pii" ? (args?.types ?? "email,phone,ssn") : undefined,
      time_ms: timeSummarize + timeClassify,
    };
  } catch (err) {
    // Bridge unavailable — degrade to sanitize-everything (flag_pii)
    console.error("[aegis-router] Bridge error, falling back to sanitize-everything:", err);
    return {
      verdict: "flag_pii",
      reason: `Bridge unavailable: ${err instanceof Error ? err.message : String(err)}`,
      confidence: 0,
      pii_types: "email,phone,ssn",
      time_ms: 0,
    };
  }
}

/**
 * Check if the Aegis bridge server is reachable.
 * Returns backend info on success, or status "unreachable" on failure.
 */
export async function healthCheck(
  config: DataGuardConfig
): Promise<BridgeHealth> {
  try {
    const resp = await getJson(config.aegisBridgeUrl, "/health", 3000);
    return {
      status: "ok",
      backend: resp.backend as BridgeHealth["backend"],
      model: resp.model as string,
    };
  } catch {
    return { status: "unreachable" };
  }
}
