const fs = require("fs");
const https = require("https");
const path = require("path");

console.log("╔════════════════════════════════════════════════════════════════╗");
console.log("║    DATAGUARD QWEN3 TOOL-CALLING PDF TEST (FINAL)             ║");
console.log("╚════════════════════════════════════════════════════════════════╝\n");

// ============ Use the PDF we already created ============
const pdfPath = "/tmp/employee_onboarding_test.pdf";

if (!fs.existsSync(pdfPath)) {
  console.error("❌ PDF not found at", pdfPath);
  process.exit(1);
}

console.log("✅ Found PDF: /tmp/employee_onboarding_test.pdf\n");

(async () => {
  try {
    // ============ STEP 1: Extract text from PDF ============
    console.log("STEP 1: Extracting text from PDF...\n");

    const { extractText } = require("./dist/sanitize/extract");
    const { text: extractedText, format } = await extractText(pdfPath, 5_000_000);

    console.log(`✅ Extracted ${extractedText.length} chars (format: ${format})`);
    console.log(`\nEXTRACTED TEXT PREVIEW:\n${"-".repeat(70)}`);
    console.log(extractedText.substring(0, 400));
    console.log("...\n");

    // ============ STEP 2: Regex baseline ============
    console.log("STEP 2: Regex PII detection (baseline)...\n");

    const { detect } = require("./dist/sanitize/detector");
    const detections = detect(extractedText);

    console.log(`Found ${detections.length} items with regex:\n`);
    const byCategory = {};
    for (const det of detections) {
      if (!byCategory[det.category]) byCategory[det.category] = [];
      byCategory[det.category].push(det);
    }
    for (const [cat, items] of Object.entries(byCategory)) {
      console.log(`  ${cat.padEnd(15)}: ${items.length}`);
    }
    console.log("");

    // ============ STEP 3: Tool-calling redaction ============
    console.log("STEP 3: Tool-calling redaction with Qwen3 Coder...\n");

    const openRouterApiKey = "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";
    const openRouterModel = "qwen/qwen3-coder";

    const TOOLS = [
      {
        type: "function",
        function: {
          name: "edit_file",
          description: "Replace exact sensitive text with a placeholder",
          parameters: {
            type: "object",
            properties: {
              old_string: { type: "string" },
              new_string: { type: "string" },
              replace_all: { type: "boolean", default: false },
            },
            required: ["old_string", "new_string"],
          },
        },
      },
      {
        type: "function",
        function: {
          name: "done_redacting",
          description: "Signal completion",
          parameters: {
            type: "object",
            properties: { summary: { type: "string" } },
            required: ["summary"],
          },
        },
      },
    ];

    let patchedText = extractedText;
    let toolCalls = [];
    let turns = 0;

    const messages = [{ role: "user", content: extractedText }];

    while (turns < 10) {
      turns++;

      const body = JSON.stringify({
        model: openRouterModel,
        messages,
        tools: TOOLS,
        temperature: 0.1,
        max_tokens: 2000,
      });

      const response = await new Promise((resolve, reject) => {
        const req = https.request(
          {
            hostname: "openrouter.ai",
            port: 443,
            path: "/api/v1/chat/completions",
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Content-Length": Buffer.byteLength(body),
              Authorization: `Bearer ${openRouterApiKey}`,
              "HTTP-Referer": "http://localhost",
            },
            timeout: 60000,
          },
          (res) => {
            let data = "";
            res.on("data", (chunk) => (data += chunk));
            res.on("end", () => {
              try {
                resolve(JSON.parse(data));
              } catch (e) {
                reject(e);
              }
            });
          }
        );

        req.on("error", reject);
        req.write(body);
        req.end();
      });

      if (response.error) {
        console.log(`⚠️  OpenRouter error: ${response.error.message}`);
        break;
      }

      const assistantMsg = response.choices?.[0]?.message;
      if (!assistantMsg?.tool_calls?.length) {
        break;
      }

      messages.push(assistantMsg);

      let done = false;
      for (const tc of assistantMsg.tool_calls) {
        const args = JSON.parse(tc.function.arguments);

        if (tc.function.name === "edit_file") {
          const { old_string, new_string, replace_all } = args;
          patchedText = replace_all 
            ? patchedText.replaceAll(old_string, new_string)
            : patchedText.replace(old_string, new_string);
          toolCalls.push({ old_string, new_string, replace_all });
          messages.push({ role: "tool", tool_call_id: tc.id, content: "OK" });
        } else if (tc.function.name === "done_redacting") {
          done = true;
          messages.push({ role: "tool", tool_call_id: tc.id, content: "OK" });
        }
      }

      if (done) break;
    }

    console.log(`✅ Completed in ${turns} turn(s)\n`);
    console.log(`Qwen3 made ${toolCalls.length} edit_file calls:\n`);

    for (let i = 0; i < Math.min(10, toolCalls.length); i++) {
      const tc = toolCalls[i];
      const oldPreview = tc.old_string.substring(0, 30).padEnd(30);
      console.log(`  ${i + 1}. edit_file("${oldPreview}", "${tc.new_string}", ${tc.replace_all})`);
    }

    if (toolCalls.length > 10) {
      console.log(`  ... and ${toolCalls.length - 10} more`);
    }
    console.log("");

    // ============ STEP 4: Results ============
    console.log("STEP 4: Final Results\n");
    console.log("─".repeat(70));
    console.log(`Original size:   ${extractedText.length} bytes`);
    console.log(`Patched size:    ${patchedText.length} bytes`);
    console.log(`Reduction:       ${((1 - patchedText.length / extractedText.length) * 100).toFixed(1)}%`);
    console.log(`Regex found:     ${detections.length} items`);
    console.log(`Tool calls:      ${toolCalls.length} replacements`);

    console.log("\n✅ PATCHED OUTPUT PREVIEW:");
    console.log("─".repeat(70));
    console.log(patchedText.substring(0, 400));
    console.log("...\n");

    const placeholders = patchedText.match(/__[A-Z_]+_\d+__/g) || [];
    const uniquePlaceholders = [...new Set(placeholders)];
    console.log(`UNIQUE PLACEHOLDERS: ${uniquePlaceholders.length}`);
    for (let i = 0; i < Math.min(15, uniquePlaceholders.length); i++) {
      console.log(`   ${uniquePlaceholders[i]}`);
    }

    console.log("\n" + "═".repeat(70));
    console.log("✅ END-TO-END TEST COMPLETE");
    console.log("═".repeat(70));

    fs.writeFileSync("/tmp/employee_onboarding_extracted.txt", extractedText);
    fs.writeFileSync("/tmp/employee_onboarding_patched.txt", patchedText);
    console.log("\nOutputs saved:");
    console.log("   Original PDF:    /tmp/employee_onboarding_test.pdf");
    console.log("   Extracted text:  /tmp/employee_onboarding_extracted.txt");
    console.log("   Patched text:    /tmp/employee_onboarding_patched.txt");

  } catch (err) {
    console.error("❌ Error:", err.message);
    process.exit(1);
  }
})();
