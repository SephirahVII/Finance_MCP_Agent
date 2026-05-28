# Output Format Rules

## Markdown

- Use one H1 title.
- Use H2 for major sections.
- Use Markdown tables for compact numeric snapshots.
- Put charts immediately after the section they support, not at the end by default.
- Always include data limitations and disclaimer.

## HTML

- Convert Markdown to a complete standalone HTML document.
- Inline CSS from `assets/report.css`.
- Preserve tables, headings, lists, and chart images.
- Use readable print-style layout: max width around 960px, clear section spacing, neutral colors.

## PDF

- Prefer HTML-to-PDF conversion from the same HTML output.
- Use print CSS with page margins.
- If PDF backend is unavailable, generate HTML and report the missing backend.
- Do not rasterize text unless absolutely necessary.

