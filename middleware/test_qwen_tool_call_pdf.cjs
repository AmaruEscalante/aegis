const fs = require("fs");
const path = require("path");
const PDFDocument = require("pdfkit");

console.log("╔════════════════════════════════════════════════════════════════╗");
console.log("║    DATAGUARD TOOL-CALLING + PDF END-TO-END TEST               ║");
console.log("╚════════════════════════════════════════════════════════════════╝\n");

// ============ STEP 1: Create a real PDF ============
console.log("STEP 1: Creating real PDF with sensitive data...\n");

const pdfPath = "/tmp/employee_onboarding_test.pdf";
const doc = new PDFDocument();
doc.pipe(fs.createWriteStream(pdfPath));

doc.fontSize(18).text("EMPLOYEE ONBOARDING FORM", { align: "center" });
doc.fontSize(10).moveDown(0.5);

doc.text("Date: 2024-02-20");
doc.text("Employee ID: EMP_12345");
doc.moveDown();

doc.fontSize(12, { underline: true }).text("PERSONAL INFORMATION");
doc.fontSize(10);
doc.text("Full Name: Michael Chen");
doc.text("Email: michael.chen@techcorp.com");
doc.text("Phone: +1 (415) 555-8901");
doc.text("Date of Birth: 1990-05-15");
doc.text("SSN: 456-78-9012");
doc.text("Address: 789 Tech Avenue, San Jose, CA 95110");
doc.moveDown();

doc.fontSize(12, { underline: true }).text("BANKING INFORMATION");
doc.fontSize(10);
doc.text("Account Number: 9876543210987654");
doc.text("Routing Number: 121000248");
doc.text("IBAN: US12SVBK0123456789");
doc.moveDown();

doc.fontSize(12, { underline: true }).text("SYSTEM CREDENTIALS (TEMPORARY)");
doc.fontSize(10);
doc.text("Temporary Password: TechSecure2024!#");
doc.text("GitHub Token: ghp_1a2b3c4d5e6f7g8h9i0j");
doc.text("AWS Access Key: AKIAIOSFODNN7EXAMPLE");
doc.text("Slack Token: xoxb-1234567890-1234567890-abcdefghijklmnop");
doc.moveDown();

doc.fontSize(12, { underline: true }).text("MANAGER");
doc.fontSize(10);
doc.text("Name: John Smith");
doc.text("Email: john.smith@techcorp.com");

doc.end();

doc.on("finish", async () => {
  console.log(`✅ PDF created: ${pdfPath}`);
  console.log(`   Size: ${fs.statSync(pdfPath).size} bytes\n`);

  // ============ STEP 2: Extract text from PDF ============
  console.log("STEP 2: Extracting text from PDF...\n");

  try {
    const { extractText } = require("/home/andres/base_last_hackathon/dataguard/dist/sanitize/extract");
    const { text: extractedText, format, sizeBytes } = await extractText(pdfPath, 5_000_000);

    console.log(`✅ Extracted ${extractedText.length} chars from PDF (format: ${format})\n`);
    console.log("EXTRACTED TEXT PREVIEW:");
    console.log("─".repeat(70));
    console.log(extractedText.substring(0, 400));
    console.log("...\n");

    // ============ STEP 3: Show detected PII (regex-only) ============
    console.log("STEP 3: Detect PII with regex (baseline)...\n");

    const { detect, applyRedactions } = require("/home/andres/base_last_hackathon/dataguard/dist/sanitize/detector");

    const detections = detect(extractedText);
    console.log(`Regex detection found: ${detections.length} items`);

    const byCategory = {};
    for (const det of detections) {
      if (!byCategory[det.category]) byCategory[det.category] = [];
      byCategory[det.category].push(det);
    }

    for (const [cat, items] of Object.entries(byCategory)) {
      console.log(`  ${cat.padEnd(15)}: ${items.length}`);
    }

    console.log("");

    // ============ STEP 4: Tool-calling redaction with Qwen ============
    console.log("STEP 4: Tool-calling redaction with Qwen3 Coder...\n");

    const openRouterApiKey = "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";
    const openRouterModel = "qwen/qwen3-coder";

    const REDACTION_TOOLS = [
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
    const https = require("https");

    async function runToolCallingLoop() {
      const messages = [{ role: "user", content: extractedText }];

      while (turns < 10) {
        turns++;

        const body = JSON.stringify({
          model: openRouterModel,
          messages,
          tools: REDACTION_TOOLS,
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
          console.log(`❌ OpenRouter error: ${response.error.message}`);
          break;
        }

        const assistantMsg = response.choices?.[0]?.message;
        if (!assistantMsg || !assistantMsg.tool_calls?.length) {
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
    }

    await runToolCallingLoop();

    console.log(`✅ Tool-calling loop completed in ${turns} turn(s)\n`);
    console.log(`Qwen made ${toolCalls.length} edit_file calls:\n`);

    for (let i = 0; i < Math.min(10, toolCalls.length); i++) {
      const tc = toolCalls[i];
      console.log(`  ${i + 1}. edit_file("${tc.old_string.substring(0, 30)}...", "${tc.new_string}", ${tc.replace_all})`);
    }

    if (toolCalls.length > 10) {
      console.log(`  ... and ${toolCalls.length - 10} more`);
    }

    console.log("");

    // ============ STEP 5: Compare results ============
    console.log("STEP 5: Comparison\n");
    console.log("─".repeat(70));
    console.log(`Original size:   ${extractedText.length} bytes`);
    console.log(`Patched size:    ${patchedText.length} bytes`);
    console.log(`Reduction:       ${((1 - patchedText.length / extractedText.length) * 100).toFixed(1)}%`);
    console.log(`Regex found:     ${detections.length} items`);
    console.log(`Tool calls made: ${toolCalls.length} replacements`);

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
    console.error("Error:", err.message);
  }
});
