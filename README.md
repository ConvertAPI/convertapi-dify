# ConvertAPI

Official [ConvertAPI](https://www.convertapi.com) plugin for Dify. Convert files between 300+ formats in your workflows, chatflows and agents: Office and HTML to PDF with layout as in Word, PDF to editable Word and Excel, merge, compress and OCR PDFs.

**Author:** ConvertAPI (UAB ConvertAPI) · **Source:** https://github.com/ConvertAPI/convertapi-dify · **Contact:** support@convertapi.com · **License:** MIT

## Tools

| Tool | What it does |
| --- | --- |
| **Convert File** | Any format pair ConvertAPI supports: DOCX → PDF, PDF → JPG, HTML → DOCX, XLSX → CSV, PPTX → PNG and more. Set the output format as a file extension. |
| **Office / HTML to PDF** | Word, Excel, PowerPoint, OpenDocument, RTF, TXT, Markdown or HTML to PDF. Optional PDF/A for archiving. |
| **PDF to Word** | PDF to editable DOCX. Scanned pages are recognized with OCR. Optional page range and password. |
| **PDF to Excel** | Extract the tables of a PDF into an XLSX workbook, one sheet per page or all on one sheet. |
| **Merge PDF** | Combine two or more PDFs into one, in the given order, with optional bookmarks per file. |
| **Compress PDF** | Shrink a PDF by up to 90% with presets from lossless to smallest. |
| **OCR PDF** | Make a scanned PDF searchable in 27 languages, or extract its text as a TXT file. |

Every tool takes Dify files as input and returns the converted files as Dify files, plus a JSON summary (file names, sizes, conversion cost). An optional **Extra parameters (JSON)** field passes any other ConvertAPI parameter, for example `{"PageRange": "1-3"}`; each converter's parameters are listed on its page at https://www.convertapi.com/api.

## Setup

1. Sign up at https://www.convertapi.com (free, no card needed) and copy an API token from https://www.convertapi.com/a/auth.
2. In Dify, open **Plugins**, install **ConvertAPI**, and click **Authorize**.
3. Paste the token. Optionally choose a processing region (EU, UK, US, Canada, Asia or Australia) to keep files in that region; the default routes to the nearest data center.
4. Add a ConvertAPI tool to a workflow, chatflow or agent and connect a file variable, for example the `sys.files` of a chat or a Start node file input.

## Usage examples

- **Contract intake:** a user uploads a DOCX in chat → **Office / HTML to PDF** → store or send the PDF.
- **Invoice extraction:** **PDF to Excel** on uploaded invoices → a Code node reads the rows.
- **Scanned archive to knowledge:** **OCR PDF** with output `txt` → feed the text to an LLM node.
- **Agent tool:** give an agent **Convert File** so it can turn any uploaded file into the format the user asks for.

## Requirements and connections

- A ConvertAPI account and API token. Each conversion uses conversions from your plan; see https://www.convertapi.com/prices.
- Outbound HTTPS from the Dify plugin runtime to `v2.convertapi.com` (or the regional host you pick: `eu-v2`, `uk-v2`, `us-v2`, `ca-v2`, `as-v2`, `au-v2` `.convertapi.com`).
- Conversions can take up to several minutes for large files or OCR; the plugin waits up to 16 minutes.
- Self-hosted Dify: the plugin reads input files from the Dify API, so the plugin daemon must reach it. With Docker Compose, set `INTERNAL_FILES_URL=http://api:5001` in `docker/.env` and restart. Without it, tools fail with "Could not read … from Dify file storage".

## Errors

When a conversion fails, the tool raises an error with a short readable message, so the workflow node fails (and Dify's error handling, such as a fail branch or retry, applies) and an agent sees what went wrong. Examples: an invalid token, no conversions left, an unsupported format pair, a wrong page range or a protected PDF without a password. The token is never included in messages or logs.

## Privacy

Files are sent to ConvertAPI for conversion and are processed in memory: the plugin requests results inline (`StoreFile=false`), so ConvertAPI does not store input or output files. See [PRIVACY.md](PRIVACY.md) and https://www.convertapi.com/compliance.

## Support

Email support@convertapi.com or open an issue at https://github.com/ConvertAPI/convertapi-dify/issues.
