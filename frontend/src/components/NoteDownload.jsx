
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx';
import { saveAs } from 'file-saver';
// --- HELPER: Parses "**Bold**" and "//Italic//" ---
const createTextRuns = (text) => {
      // Regex explanation:
      // (\*\*.*?\*\*)  -> Matches **text**
      // |               -> OR
      // (\/\/.*?\/\/)   -> Matches //text//
      // The wrapping parentheses () capture the delimiters so we can inspect them
      const parts = text.split(/(\*\*.*?\*\*|\/\/.*?\/\/)/g);

      return parts.map((part) => {
            // 1. Check for **BOLD**
            if (part.startsWith('**') && part.endsWith('**')) {
                  return new TextRun({
                        text: part.slice(2, -2), // Remove stars
                        bold: true,
                        font: "Iskoola Pota",
                        size: 24
                  });
            }

            // 2. Check for //ITALIC//
            if (part.startsWith('//') && part.endsWith('//')) {
                  return new TextRun({
                        text: part.slice(2, -2), // Remove slashes
                        italics: true,           // <--- Set Italic
                        font: "Iskoola Pota",
                        size: 24
                  });
            }

            // 3. Normal Text (ignore empty strings)
            if (!part) return null;

            return new TextRun({
                  text: part,
                  bold: false,
                  italics: false,
                  font: "Iskoola Pota",
                  size: 24
            });
      }).filter(Boolean); // Remove any nulls
};
// --- 1. Update Function to accept 'content' argument ---
const generateWordDocument = (content) => {
      if (!content) return;

      const lines = content.trim().split('\n');

      const docChildren = lines.map((line) => {
            const cleanLine = line.trim();

            // --- CHECK HEADINGS (Order matters: longest first!) ---

            // Level 3 (###)
            if (cleanLine.startsWith('### ')) {
                  return new Paragraph({
                        children: [
                              new TextRun({
                                    text: cleanLine.replace('# ', ''),
                                    font: "Iskoola Pota",
                                    bold: true,
                                    size: 28 // <--- 18pt (Big Title)
                              })
                        ],
                        // children: createTextRuns(cleanLine.replace('### ', '')),
                        heading: HeadingLevel.HEADING_3,
                        spacing: { after: 120 }

                  });
            }

            // Level 2 (##)
            if (cleanLine.startsWith('## ')) {
                  return new Paragraph({
                        children: [
                              new TextRun({
                                    text: cleanLine.replace('# ', ''),
                                    font: "Iskoola Pota",
                                    bold: true,
                                    size: 30 // <--- 18pt (Big Title)
                              })
                        ],
                        // children: createTextRuns(cleanLine.replace('## ', '')),
                        heading: HeadingLevel.HEADING_2,
                        spacing: { after: 150 }

                  });
            }

            // Level 1 (#)
            if (cleanLine.startsWith('# ')) {
                  return new Paragraph({
                        children: [
                              new TextRun({
                                    text: cleanLine.replace('# ', ''),
                                    font: "Iskoola Pota",
                                    bold: true,
                                    size: 36 // <--- 18pt (Big Title)
                              })
                        ],
                        // children: createTextRuns(cleanLine.replace('# ', '')),
                        heading: HeadingLevel.HEADING_1,
                        spacing: { after: 200 }
                  });
            }

            // --- CHECK BULLETS ---
            if (cleanLine.startsWith('* ')) {
                  return new Paragraph({
                        children: createTextRuns(cleanLine.replace('* ', '')),
                        bullet: { level: 0 },
                        spacing: { after: 100 }
                  });
            }

            // --- NORMAL PARAGRAPH ---
            // Ignore empty lines to keep document tight
            if (cleanLine === '') return new Paragraph({});

            return new Paragraph({
                  children: createTextRuns(cleanLine),
                  spacing: { after: 100 }
            });
      });

      // Build & Save
      const doc = new Document({
            sections: [{ children: docChildren }]
      });

      Packer.toBlob(doc).then((blob) => {
            saveAs(blob, "Lecture_Note.docx");
      });
};

export default generateWordDocument;