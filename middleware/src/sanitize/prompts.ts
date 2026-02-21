// ============================================================================
// SANITIZATION PROMPTS FOR OLLAMA GEMMA
// ============================================================================

import type { PdfTextToken } from "../types";

/**
 * Build the system prompt for sanitization.
 * Instructs Gemma to identify and replace PII/secrets with placeholders.
 *
 * We pass the regex-pre-redacted text to Ollama to avoid sending raw secrets
 * to the model. This means Ollama's improvements are limited to cases where
 * regex didn't catch something, but it's a reasonable security trade-off.
 */
export function buildSanitizePrompt(
  text: string,
  regexRedacted: string
): string {
  return `You are a data-privacy sanitization engine. Your task is to identify and replace
all personally identifiable information (PII) and secrets in the following text.

Categories to detect and replace:
- EMAIL addresses (format: user@domain.com)
- PHONE numbers (various formats)
- SSNs (format: XXX-XX-XXXX)
- CREDIT CARD numbers
- IBANs
- API keys, tokens, passwords (SECRET category)
- IP addresses
- URLs containing user data or credentials
- Any other sensitive identifiers (names, addresses, medical info, etc.)

Replacement format: __<CATEGORY>_<n>__ where n is a counter starting at 1 per category.
Example outputs:
- First email: __EMAIL_1__
- Second email: __EMAIL_2__
- First secret: __SECRET_1__

IMPORTANT RULES:
1. Preserve ALL non-sensitive text exactly, including whitespace, formatting, newlines
2. Do NOT redact generic technical terms (localhost, example, test, etc.)
3. Do NOT redact variable names, function names, or code structure words
4. Do NOT redact public domain names used as examples (example.com, localhost, 127.0.0.1)
5. The regex pre-pass has already replaced some items — preserve those placeholders as-is
6. Use the exact placeholder format: __CATEGORY_n__ (underscore-underscore, uppercase, underscore-underscore)

Respond ONLY with valid JSON in this exact schema (NO markdown code fences, NO explanation text, ONLY the JSON object):
{
  "sanitized_text": "<full text with all replacements applied>",
  "redactions": [
    {
      "type": "<CATEGORY>",
      "placeholder": "__<CATEGORY>_<n>__",
      "context": "<5 words of surrounding context>"
    }
  ],
  "summary": "<one sentence describing what was found and redacted>"
}

TEXT TO SANITIZE:
---
${regexRedacted}
---`;
}

/**
 * Build the prompt for coordinate-based PDF visual redaction.
 *
 * Tokens are passed as a compact list: id|text
 * The LLM selects which IDs to redact and provides a reason.
 * We never send bounding-box coordinates to the LLM — those are
 * resolved server-side. This keeps prompts small and prevents
 * coordinate confusion in the model's reasoning.
 *
 * Security note: regex pre-pass has already flagged some tokens.
 * The LLM's job is to catch what regex missed.
 */
export function buildPdfRedactPrompt(tokens: PdfTextToken[]): string {
  // Serialize tokens as a compact line-per-token table: "id|text"
  // We cap at 800 tokens to keep the prompt under Gemma's context window.
  const cap = Math.min(tokens.length, 800);
  const tokenList = tokens
    .slice(0, cap)
    .map((t) => `${t.id}|${t.text}`)
    .join("\n");

  return `You are a PII detection engine for PDF visual redaction. Below is a list of text tokens extracted from a PDF. Each line is: TOKEN_ID|TEXT

Your task: identify which token IDs contain personally identifiable information (PII) or secrets that must be visually redacted (blacked out).

Categories to redact:
- Person names (first, last, full names)
- EMAIL addresses
- Phone numbers
- Social Security Numbers (SSN format: XXX-XX-XXXX)
- Credit card numbers
- Bank account numbers / IBANs
- Passport or government ID numbers
- Physical addresses (street, city, postal code combinations)
- API keys, tokens, passwords, secrets (sk-, pk-, ghp-, AKIA, etc.)
- IP addresses used in private contexts
- Any other clearly sensitive personal identifiers

Do NOT redact:
- Generic technical terms, code keywords, field labels ("Name:", "Email:", "Date:")
- Public example values (example.com, localhost, 127.0.0.1, test@test.com)
- Page numbers, headers, footers with generic text
- Dates that are not birth dates or sensitive event dates

TOKENS:
---
${tokenList}
---

Respond ONLY with valid JSON, NO markdown fences, NO explanation text:
{
  "redact": [
    { "id": <token_id_integer>, "reason": "<CATEGORY: brief explanation>" }
  ],
  "summary": "<one sentence: what PII was found>"
}

If no PII is found, return: {"redact": [], "summary": "No PII detected"}`;
}

/**
 * Build prompt for comprehensive LLM-based PII analysis of full document content.
 *
 * This is more aggressive than coordinate-level detection — the LLM reads the
 * full text and identifies all sensitive items, which we then locate in the PDF
 * and redact comprehensively.
 *
 * Returns JSON with array of sensitive_items: [{type, value, context, reason}]
 */
export function buildLlmPiiAnalysisPrompt(text: string): string {
  return `You are a comprehensive data privacy analyzer. Your task is to identify ALL personally identifiable information (PII), secrets, and sensitive data in the following document.

For each sensitive item found, provide:
1. The exact text (must be a direct quote from the document)
2. Category (EMAIL, PHONE, SSN, CREDIT_CARD, IBAN, SECRET, URL, IP_ADDRESS, NAME, ADDRESS, etc.)
3. A snippet of surrounding context (20 words before and after)
4. Reason why it should be redacted

Categories to find and redact:
- Person names (individuals' first, middle, last names)
- EMAIL addresses (name@domain.com format)
- Phone numbers (any format: +1-555-123-4567, 555.123.4567, etc.)
- Social Security Numbers (XXX-XX-XXXX, no-dash variations)
- Credit card numbers (15-19 digits)
- Bank account numbers (IBANs, BBANs)
- Passport numbers, driver license numbers
- Government ID numbers
- Physical addresses (street, city, state, zip combinations)
- API keys and tokens (sk-, pk-, ghp-, AKIA, xox-, Bearer, etc.)
- Database passwords and credentials
- Private IP addresses in configuration contexts
- Medical information (diagnoses, treatment details)
- Financial information (salary, account balances, transaction details)
- Trade secrets or confidential business data

Do NOT redact:
- Generic example values (example.com, 127.0.0.1, test@test.com, "Name:", "Email:", "Date:")
- Public company names used in context
- Generic technical terms and code keywords
- Public documentation URLs
- Standard field labels and headers

DOCUMENT TEXT:
---
${text}
---

Respond ONLY with valid JSON, NO markdown fences, NO explanation:
{
  "sensitive_items": [
    {
      "type": "<CATEGORY>",
      "value": "<exact text from document>",
      "context": "<20 words before and after>",
      "reason": "<why this should be redacted>"
    }
  ],
  "summary": "<2-3 sentences about what sensitive data was found>"
}

If no sensitive data found, return: {"sensitive_items": [], "summary": "No sensitive data detected"}`;
}
