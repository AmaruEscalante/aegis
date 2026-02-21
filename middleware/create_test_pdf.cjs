const fs = require("fs");
const PDFDocument = require("pdfkit");

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

doc.on("finish", () => {
  console.log("✅ PDF created: " + pdfPath);
});
