// ============================================================================
// AEGIS_SEARCH TOOL — Search with sanitized results
// ============================================================================

import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import type { DataGuardConfig } from "../types";
import { checkPath } from "../sanitize/policy";
import { sanitize } from "../sanitize/sanitize";
import { log } from "../sanitize/audit";

export interface DataguardSearchParams {
  query: string;
  root: string;
  maxResults?: number;
}

export interface SearchSnippet {
  file: string;
  line: number;
  sanitized_snippet: string;
}

export interface DataguardSearchResult {
  snippets: SearchSnippet[];
  total_matches: number;
}

/**
 * Create the dataguard_search tool handler.
 * Searches files under a root directory, returns sanitized snippets only.
 */
export function createDataguardSearch(config: DataGuardConfig) {
  return async function dataguardSearch(
    params: DataguardSearchParams
  ): Promise<DataguardSearchResult> {
    const rootCheck = checkPath(params.root, config);
    if (rootCheck.verdict === "deny") {
      throw new Error(`Aegis denied access to root: ${rootCheck.reason}`);
    }

    const absRoot = path.resolve(params.root);
    const maxResults = params.maxResults ?? 20;
    const query = params.query;

    // --- Step 1: Search using rg (ripgrep) or grep ---
    let rawOutput: string;
    try {
      // Try ripgrep first (faster, better output format)
      rawOutput = execSync(
        `rg --json -m ${maxResults} ${JSON.stringify(query)} ${JSON.stringify(absRoot)}`,
        { maxBuffer: 5 * 1024 * 1024, timeout: 15_000 }
      ).toString("utf-8");
    } catch (e: any) {
      // Fallback to grep
      try {
        rawOutput = execSync(
          `grep -rn --include="*" -m ${maxResults} ${JSON.stringify(query)} ${JSON.stringify(absRoot)}`,
          { maxBuffer: 5 * 1024 * 1024, timeout: 15_000 }
        ).toString("utf-8");
      } catch {
        // No matches or error
        return { snippets: [], total_matches: 0 };
      }
    }

    // --- Step 2: Parse results and sanitize ---
    const snippets: SearchSnippet[] = [];

    for (const line of rawOutput.split("\n")) {
      if (!line.trim()) continue;

      try {
        // Try parsing as ripgrep JSON first
        const obj = JSON.parse(line);
        if (obj.type === "match") {
          const filePath = obj.data.path.text;
          const lineNum = obj.data.line_number;
          const text = obj.data.lines.text;

          const result = await sanitize(text, config);
          snippets.push({
            file: filePath,
            line: lineNum,
            sanitized_snippet: result.sanitized_text.trim(),
          });
        }
      } catch {
        // Not JSON — might be grep output or malformed
        // Try parsing as grep format: file:linenum:content
        const match = line.match(/^([^:]+):(\d+):(.*)$/);
        if (match) {
          const filePath = match[1];
          const lineNum = parseInt(match[2], 10);
          const text = match[3];

          const result = await sanitize(text, config);
          snippets.push({
            file: filePath,
            line: lineNum,
            sanitized_snippet: result.sanitized_text.trim(),
          });
        }
      }
    }

    // --- Step 3: Audit log ---
    log({
      timestamp: new Date().toISOString(),
      event: "aegis_search",
      action: "sanitize",
      reason: `query: ${query}, ${snippets.length} results`,
    });

    return {
      snippets,
      total_matches: snippets.length,
    };
  };
}
