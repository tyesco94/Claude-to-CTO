---
name: research-auditor
description: Audit a PDF report, research paper, or long document for internal contradictions, unsupported claims, math errors, and chart/text mismatches, then present findings as a filterable severity dashboard. Use when the user asks to audit, fact-check, review, or sanity-check a report.
---

# Deep Research Auditor

## Process
1. **Read the full document.** Extract text per page. Render each page with charts/tables as an image and inspect it visually — numbers in charts often disagree with the text.
2. **Build a claims ledger**: every numeric claim, key assertion and conclusion, with page number.
3. **Check for:**
   - Contradictions — same metric stated differently in two places.
   - Math errors — percentages that don't add up, wrong growth calcs, totals ≠ sum of parts.
   - Chart/text mismatch.
   - Unsupported claims — conclusions with no data or citation.
   - Methodology gaps — sample size, timeframe, definitions missing or changing.
   - Signs of AI-generated filler — vague claims, fake-looking citations (flag, don't assert).
4. **Rate each finding**: High (changes a conclusion), Medium (misleading), Low (sloppy/cosmetic).
5. **Output a single HTML dashboard**:
   - Summary bar: total findings + count by severity + one-line overall trust verdict.
   - Filter buttons: All / High / Medium / Low.
   - Each finding card: severity, title, page(s), exact quotes side by side, why it matters, suggested fix.
6. In chat, give the top 3 findings and the overall verdict.

## Rules
- Quote exactly; always cite page numbers.
- Don't flag something as wrong unless you can show why. If unsure, label it "Needs verification".
