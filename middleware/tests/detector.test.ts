import { describe, it, expect } from "vitest";
import { detect, applyRedactions } from "../src/sanitize/detector";

describe("detector", () => {
  describe("detect()", () => {
    it("detects email addresses", () => {
      const hits = detect("Contact alice@example.com for info");
      expect(hits).toHaveLength(1);
      expect(hits[0].category).toBe("EMAIL");
      expect(hits[0].value).toBe("alice@example.com");
      expect(hits[0].placeholder).toBe("__EMAIL_1__");
    });

    it("detects multiple emails with incrementing placeholders", () => {
      const hits = detect(
        "Email 1: alice@example.com, Email 2: bob@company.org"
      );
      expect(hits).toHaveLength(2);
      expect(hits[0].placeholder).toBe("__EMAIL_1__");
      expect(hits[1].placeholder).toBe("__EMAIL_2__");
    });

    it("detects SSN format XXX-XX-XXXX", () => {
      const hits = detect("SSN: 123-45-6789");
      expect(hits).toHaveLength(1);
      expect(hits[0].category).toBe("SSN");
      expect(hits[0].value).toBe("123-45-6789");
    });

    it("detects GitHub tokens (ghp_)", () => {
      const token = "ghp_" + "a".repeat(36);
      const hits = detect(`token: ${token}`);
      expect(hits).toHaveLength(1);
      expect(hits[0].category).toBe("SECRET");
    });

    it("detects API keys with sk- prefix", () => {
      const token = "sk_live_" + "x".repeat(20);
      const hits = detect(`key: ${token}`);
      expect(hits.length).toBeGreaterThan(0);
      expect(hits[0].category).toBe("SECRET");
    });

    it("detects credit card numbers (Visa, Mastercard, Amex)", () => {
      const visa = "4532-1234-5678-9010";
      const mc = "5105-1051-0510-5100";

      const visaHits = detect(`Card: ${visa}`);
      const mcHits = detect(`Card: ${mc}`);

      expect(visaHits.length).toBeGreaterThan(0);
      expect(mcHits.length).toBeGreaterThan(0);
      expect(visaHits[0].category).toBe("CREDIT_CARD");
    });

    it("detects IP addresses", () => {
      const hits = detect("Server: 192.168.1.1");
      expect(hits).toHaveLength(1);
      expect(hits[0].category).toBe("IP_ADDRESS");
      expect(hits[0].value).toBe("192.168.1.1");
    });

    it("detects URLs", () => {
      const hits = detect("Visit https://api.example.com/v1/endpoint");
      expect(hits.length).toBeGreaterThan(0);
      expect(hits[0].category).toBe("URL");
    });

    it("detects phone numbers in various formats", () => {
      const formats = [
        "+1 (555) 123-4567",
        "555-123-4567",
        "5551234567",
        "+1.555.123.4567"
      ];

      for (const fmt of formats) {
        const hits = detect(`Phone: ${fmt}`);
        expect(hits.length).toBeGreaterThan(0, `Failed for format: ${fmt}`);
      }
    });

    it("detects high-entropy tokens", () => {
      // 32-char base64-ish string with high entropy
      const token = "Xk9mP2qR7vB4nL8wJ5tY3hC6dE1fA0gZ";
      const hits = detect(`token: ${token}`);

      // Should have at least one detection (the high-entropy token)
      expect(hits.length).toBeGreaterThan(0);
      expect(hits.some((h) => h.category === "HIGH_ENTROPY")).toBe(true);
    });

    it("does not double-tag overlapping patterns", () => {
      const text = "Email: a@b.com Phone: 555-123-4567 end";
      const hits = detect(text);

      // Check that no two hits overlap
      const offsets = hits.map((h) => ({ start: h.start, end: h.end }));
      for (let i = 0; i < offsets.length - 1; i++) {
        expect(offsets[i].end).toBeLessThanOrEqual(offsets[i + 1].start);
      }
    });

    it("sorts detections by start offset", () => {
      const text = "Phone: 555-123-4567, Email: alice@example.com";
      const hits = detect(text);

      // Check sorted ascending by start
      for (let i = 0; i < hits.length - 1; i++) {
        expect(hits[i].start).toBeLessThan(hits[i + 1].start);
      }
    });
  });

  describe("applyRedactions()", () => {
    it("replaces matched regions with placeholders", () => {
      const text = "Email: alice@example.com";
      const hits = detect(text);
      const result = applyRedactions(text, hits);

      expect(result).toContain("__EMAIL_1__");
      expect(result).not.toContain("alice@example.com");
    });

    it("preserves non-matched text exactly", () => {
      const text = "Contact alice@example.com for support.";
      const hits = detect(text);
      const result = applyRedactions(text, hits);

      expect(result).toContain("Contact");
      expect(result).toContain("for support.");
      expect(result).not.toContain("alice@example.com");
    });

    it("handles multiple redactions without offset drift", () => {
      const text =
        "Email: a@b.com, Phone: 555-123-4567, SSN: 123-45-6789";
      const hits = detect(text);
      const result = applyRedactions(text, hits);

      expect(result).not.toContain("a@b.com");
      expect(result).not.toContain("555-123-4567");
      expect(result).not.toContain("123-45-6789");
      expect(result).toContain("Email:");
      expect(result).toContain("Phone:");
      expect(result).toContain("SSN:");
    });

    it("preserves whitespace and formatting", () => {
      const text = "User email:   alice@example.com\n\nPassword: abc123";
      const hits = detect(text);
      const result = applyRedactions(text, hits);

      expect(result).toContain("User email:");
      expect(result).toContain("   "); // Preserves spacing
      expect(result).toContain("\n\n"); // Preserves newlines
      expect(result).toContain("Password:");
    });

    it("handles empty detections list", () => {
      const text = "No secrets here";
      const result = applyRedactions(text, []);
      expect(result).toBe(text);
    });

    it("applies redactions in correct order (left-to-right)", () => {
      const text = "abc def ghi";
      const detections = [
        {
          category: "EMAIL",
          value: "abc",
          start: 0,
          end: 3,
          placeholder: "__A__",
        },
        {
          category: "EMAIL",
          value: "def",
          start: 4,
          end: 7,
          placeholder: "__B__",
        },
      ];

      const result = applyRedactions(text, detections);
      expect(result).toBe("__A__ __B__ ghi");
    });
  });
});
