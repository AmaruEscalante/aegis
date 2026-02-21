// ============================================================================
// SANITIZATION ORCHESTRATION — Regex + LLM
// ============================================================================

import http from "http";
import https from "https";
import type { DataGuardConfig, SanitizeResult, Detection } from "../types";
import { detect, applyRedactions } from "./detector";
import { buildSanitizePrompt } from "./prompts";
import { addMappings } from "./vault";

/**
 * Call Ollama's chat API endpoint with a prompt.
 * Uses Node's built-in http module (no external dependencies).
 * Returns the LLM's response text.
 */
function ollamaChat(
  baseUrl: string,
  model: string,
  prompt: string,
  timeoutMs: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      stream: false, // Non-streaming response
    });

    const url = new URL(`${baseUrl}/api/chat`);
    const hostname = url.hostname || "127.0.0.1";
    const port = Number(url.port) || 11434;
    const pathname = url.pathname || "/api/chat";

    const req = http.request(
      {
        hostname,
        port,
        path: pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let data = "";

        res.on("data", (chunk: Buffer) => {
          data += chunk.toString("utf-8");
        });

        res.on("end", () => {
          try {
            const parsed = JSON.parse(data);
            // Ollama non-streaming response: { message: { content: "..." } }
            const content = parsed?.message?.content ?? "";
            resolve(content);
          } catch (err) {
            reject(new Error(`Failed to parse Ollama response: ${err}`));
          }
        });
      }
    );

    req.setTimeout(timeoutMs, () => {
      req.destroy();
      reject(new Error(`Ollama request timed out after ${timeoutMs}ms`));
    });

    req.on("error", (err) => {
      reject(new Error(`Ollama request failed: ${err.message}`));
    });

    req.write(body);
    req.end();
  });
}

/**
 * Call OpenRouter's chat API endpoint with a prompt.
 * Uses Node's built-in https module (no external dependencies).
 * Returns the LLM's response text.
 */
function openrouterChat(
  apiKey: string,
  model: string,
  prompt: string,
  timeoutMs: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.1,
      max_tokens: 2000,
    });

    const req = https.request(
      {
        hostname: "openrouter.ai",
        port: 443,
        path: "/api/v1/chat/completions",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
          Authorization: `Bearer ${apiKey}`,
          "HTTP-Referer": "dataguard-plugin",
          "X-Title": "DataGuard",
        },
      },
      (res) => {
        let data = "";

        res.on("data", (chunk: Buffer) => {
          data += chunk.toString("utf-8");
        });

        res.on("end", () => {
          try {
            const parsed = JSON.parse(data);

            // Check for OpenRouter API errors
            if (parsed.error) {
              reject(new Error(`OpenRouter error: ${parsed.error.message || "Unknown error"}`));
              return;
            }

            // OpenRouter response: { choices: [{ message: { content: "..." } }] }
            const content = parsed?.choices?.[0]?.message?.content ?? "";
            resolve(content);
          } catch (err) {
            reject(new Error(`Failed to parse OpenRouter response: ${err}`));
          }
        });
      }
    );

    req.setTimeout(timeoutMs, () => {
      req.destroy();
      reject(new Error(`OpenRouter request timed out after ${timeoutMs}ms`));
    });

    req.on("error", (err) => {
      reject(new Error(`OpenRouter request failed: ${err.message}`));
    });

    req.write(body);
    req.end();
  });
}

/**
 * Tool Calling Mode — Qwen3 Coder uses edit_file() tool calls for surgical replacements.
 * Mirrors Claude Code's Edit tool: old_string + new_string + replace_all parameter.
 */
const REDACTION_TOOLS = [
  {
    type: "function",
    function: {
      name: "edit_file",
      description:
        "Perform a precise string replacement to redact sensitive data. Replaces old_string with new_string (a placeholder like __EMAIL_1__). Use replace_all=true if the same value appears multiple times.",
      parameters: {
        type: "object",
        properties: {
          old_string: {
            type: "string",
            description: "Exact text to find and redact",
          },
          new_string: {
            type: "string",
            description: 'Placeholder to replace it with, e.g. __EMAIL_1__, __PASSWORD_1__',
          },
          replace_all: {
            type: "boolean",
            default: false,
            description: "Replace all occurrences if same value appears multiple times",
          },
        },
        required: ["old_string", "new_string"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "done_redacting",
      description: "Signal that all sensitive data has been found and replaced",
      parameters: {
        type: "object",
        properties: {
          summary: {
            type: "string",
            description: "Brief summary of what was redacted",
          },
        },
        required: ["summary"],
      },
    },
  },
];

/**
 * OpenRouter tool-calling redaction via Qwen3 Coder.
 * Qwen makes edit_file() tool calls, we execute them locally as string replacements.
 */
async function openrouterToolCallRedact(
  text: string,
  apiKey: string,
  model: string,
  timeoutMs: number
): Promise<{ patchedText: string; redactions: Array<{ old_string: string; new_string: string; replace_all: boolean }> }> {
  const systemPrompt = `You are a data redaction tool. The document below contains sensitive PII and credentials.

Use the edit_file tool to surgically replace EACH sensitive value with a placeholder.

Placeholder naming rules:
- __EMAIL_N__, __PHONE_N__, __SSN_N__, __PASSWORD_N__, __API_KEY_N__, __TOKEN_N__
- __ADDRESS_N__, __CREDIT_CARD_N__, __IBAN_N__, __NAME_N__, __DATE_N__
- __ACCOUNT_NUMBER_N__, __ROUTING_NUMBER_N__, __EMPLOYEE_ID_N__, __PASSPORT_N__, __DRIVER_LICENSE_N__
- N increments per category (EMAIL_1, EMAIL_2, EMAIL_3, etc.)

Rules:
- Call edit_file once per unique sensitive value
- Use replace_all=true if the same value appears multiple times in the document
- Only redact genuinely sensitive data — preserve structure, labels, and non-sensitive text
- When you have redacted all sensitive data, call done_redacting()`;

  const messages: any[] = [
    { role: "user", content: text },
  ];

  let patchedText = text;
  const redactions: Array<{ old_string: string; new_string: string; replace_all: boolean }> = [];
  const maxTurns = 15;
  let turn = 0;

  while (turn < maxTurns) {
    turn++;

    // Request from Qwen with tools
    const body = JSON.stringify({
      model,
      messages,
      tools: REDACTION_TOOLS,
      temperature: 0.1,
      max_tokens: 2000,
    });

    const response = await new Promise<any>((resolve, reject) => {
      const req = https.request(
        {
          hostname: "openrouter.ai",
          port: 443,
          path: "/api/v1/chat/completions",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
            Authorization: `Bearer ${apiKey}`,
            "HTTP-Referer": "dataguard-tool-calling",
            "X-Title": "DataGuard Tool-Calling",
          },
        },
        (res) => {
          let data = "";
          res.on("data", (chunk: Buffer) => {
            data += chunk.toString("utf-8");
          });
          res.on("end", () => {
            try {
              resolve(JSON.parse(data));
            } catch (err) {
              reject(new Error(`Failed to parse OpenRouter response: ${err}`));
            }
          });
        }
      );

      req.setTimeout(timeoutMs, () => {
        req.destroy();
        reject(new Error(`OpenRouter tool-calling request timed out`));
      });

      req.on("error", (err) => {
        reject(new Error(`OpenRouter request failed: ${err.message}`));
      });

      req.write(body);
      req.end();
    });

    // Check for API errors
    if (response.error) {
      throw new Error(`OpenRouter error: ${response.error.message}`);
    }

    const assistantMessage = response.choices?.[0]?.message;
    if (!assistantMessage) {
      break; // No more messages
    }

    // Add assistant message to conversation
    messages.push(assistantMessage);

    // Process tool calls
    const toolCalls = assistantMessage.tool_calls || [];
    if (toolCalls.length === 0) {
      break; // No tool calls, LLM finished
    }

    let doneRedacting = false;

    for (const toolCall of toolCalls) {
      const toolName = toolCall.function.name;
      const toolArgs = JSON.parse(toolCall.function.arguments);

      if (toolName === "edit_file") {
        const { old_string, new_string, replace_all } = toolArgs;

        // Execute replacement
        if (replace_all) {
          patchedText = patchedText.replaceAll(old_string, new_string);
        } else {
          patchedText = patchedText.replace(old_string, new_string);
        }

        redactions.push({ old_string, new_string, replace_all });

        // Send success response
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: "Replaced successfully",
        });
      } else if (toolName === "done_redacting") {
        doneRedacting = true;
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: "Redaction complete",
        });
      }
    }

    if (doneRedacting) {
      break; // LLM signaled done
    }
  }

  return { patchedText, redactions };
}

/**
 * Parse JSON response from LLM (Ollama or OpenRouter).
 * Strips markdown code fences if present (models sometimes wrap in ```json```).
 * Returns parsed object or null if parsing fails.
 */
function parseLlmJson(raw: string): {
  sanitized_text: string;
  redactions: Array<{ type: string; placeholder: string; context: string }>;
  summary?: string;
} | null {
  // Strip markdown code fences if present
  const stripped = raw
    .replace(/^```(?:json)?\s*/m, "")
    .replace(/```\s*$/m, "")
    .trim();

  try {
    return JSON.parse(stripped);
  } catch {
    return null;
  }
}

/**
 * Call the appropriate LLM provider (Ollama or OpenRouter).
 * Handles provider selection and error handling.
 */
async function callLlm(
  text: string,
  regexRedacted: string,
  config: DataGuardConfig
): Promise<string> {
  const prompt = buildSanitizePrompt(text, regexRedacted);

  if (config.llmProvider === "openrouter") {
    // Use OpenRouter cloud LLM
    return await openrouterChat(
      config.openrouterApiKey,
      config.openrouterModel,
      prompt,
      config.openrouterTimeoutMs
    );
  } else {
    // Default to Ollama local LLM
    return await ollamaChat(
      config.ollamaBaseUrl,
      config.ollamaModel,
      prompt,
      config.ollamaTimeoutMs
    );
  }
}

/**
 * Sanitize text using regex detection + optional LLM refinement.
 *
 * Flow:
 *  1. Regex pass: detect PII/secrets, build placeholders, store in vault
 *  2. LLM pass (optional): send regex-redacted text to Ollama/OpenRouter for further refinement
 *  3. If LLM fails: fall back to regex-only result
 *  4. Return sanitized text + redactions + method used
 */
export async function sanitize(
  text: string,
  config: DataGuardConfig
): Promise<SanitizeResult> {

  // --- PASS 1: Regex + Entropy Detection ---
  const regexDetections = detect(text);
  const regexRedacted = applyRedactions(text, regexDetections);

  // Store regex detections in vault immediately
  addMappings(
    regexDetections.map((d) => ({
      placeholder: d.placeholder,
      original: d.value,
      category: d.category,
    }))
  );

  // --- PASS 2: LLM Refinement (Optional) ---
  try {
    // Check if using tool-calling mode with OpenRouter
    if (config.llmProvider === "openrouter" && config.llmMode === "tool-calling") {
      // Tool-calling mode: Qwen makes edit_file() calls, we execute locally
      const { patchedText, redactions: toolRedactions } = await openrouterToolCallRedact(
        text,
        config.openrouterApiKey,
        config.openrouterModel,
        config.openrouterTimeoutMs
      );

      // Convert tool redactions to Detection format
      const toolDetections: Detection[] = toolRedactions.map((tc, idx) => ({
        category: "HIGH_ENTROPY", // Tool-calling doesn't categorize, so mark as HIGH_ENTROPY
        value: tc.old_string,
        start: -1,
        end: -1,
        placeholder: tc.new_string,
      }));

      // Store tool-call discoveries in vault
      addMappings(
        toolDetections.map((d) => ({
          placeholder: d.placeholder,
          original: d.value,
          category: d.category,
        }))
      );

      // Merge with regex detections
      const allDetections = [...regexDetections, ...toolDetections];

      return {
        sanitized_text: patchedText,
        redactions: allDetections,
        llm_summary: `Tool-calling mode: ${toolRedactions.length} items redacted`,
        method: "llm+regex",
      };
    } else {
      // Prompt mode: traditional approach (return full rewritten document)
      const rawResp = await callLlm(text, regexRedacted, config);
      const parsed = parseLlmJson(rawResp);
      if (!parsed || !parsed.sanitized_text) {
        throw new Error("LLM returned invalid JSON structure");
      }

      // LLM's sanitized text is canonical
      // Re-run detector on LLM output to find any new placeholders it introduced
      const llmDetections = detect(parsed.sanitized_text);

      // Build Detection objects from LLM redactions
      // (note: we lose exact byte offsets from LLM, so we use -1)
      const llmDets: Detection[] = (parsed.redactions || []).map((r: any) => ({
        category: (r.type as any) ?? "HIGH_ENTROPY",
        value: r.context || "(redacted)",
        start: -1, // Not applicable post-LLM
        end: -1,
        placeholder: r.placeholder,
      }));

      // Store LLM-discovered mappings in vault
      addMappings(
        llmDets.map((d) => ({
          placeholder: d.placeholder,
          original: d.value,
          category: d.category,
        }))
      );

      // Merge all detections (regex + LLM)
      const allDetections = [...regexDetections, ...llmDets];

      return {
        sanitized_text: parsed.sanitized_text,
        redactions: allDetections,
        llm_summary: parsed.summary,
        method: "llm+regex",
      };
    }

  } catch (err) {
    // LLM failed (timeout, connection error, parse error, etc.)
    // Fall back to regex-only result
    return {
      sanitized_text: regexRedacted,
      redactions: regexDetections,
      method: "regex-only",
    };
  }
}
