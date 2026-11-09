# Plugin Submission

## Plugin information

- **Author**: convertapi
- **Plugin name**: convertapi
- **Version**: 0.1.0
- **Source repository**: https://github.com/ConvertAPI/convertapi-dify
- **Contact**: support@convertapi.com

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

This is the official ConvertAPI plugin, built and maintained by us at ConvertAPI (https://www.convertapi.com). It adds seven tools that take Dify files and return the converted files as Dify files:

- **Convert File**: any of the 300+ format pairs ConvertAPI supports (DOCX → PDF, PDF → JPG, HTML → DOCX, XLSX → CSV and so on)
- **Office / HTML to PDF**: Word, Excel, PowerPoint, OpenDocument, RTF, TXT, Markdown and HTML to PDF, optionally PDF/A
- **PDF to Word** and **PDF to Excel**
- **Merge PDF**, **Compress PDF** and **OCR PDF** (searchable PDF or plain text, 27 languages)

Authorization is a ConvertAPI API token, with an optional processing region (EU, UK, US, Canada, Asia, Australia). Errors such as a wrong token, no conversions left, an unsupported format pair or an invalid page range raise a short readable message, so the workflow node fails and Dify's error handling applies.

## Risk level

- [ ] Low risk
- [x] Medium risk
- [ ] High risk

The plugin processes user-uploaded files and sends them to an external service (ConvertAPI) for conversion.

## Required checks

- [x] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the [Plugin Development Guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct).
- [ ] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

- File operations: the plugin reads the files passed to a tool from Dify and uploads them over HTTPS to ConvertAPI. It does not touch the local filesystem.
- Network: requests go only to fixed ConvertAPI hosts (`v2.convertapi.com` or one of the regional `*-v2.convertapi.com` hosts picked from a fixed list). There is no user-controlled URL or arbitrary URL fetching.
- Results are requested inline (`StoreFile=false`), so ConvertAPI converts in memory and does not store the files.
- The token is sent only in the `Authorization` header and is never included in messages or errors. Requests have connect and read timeouts.
- An optional "Extra parameters (JSON)" field passes conversion options to ConvertAPI; it cannot override the file, token or storage fields.

## Local validation

```
$ pytest -v            # plugin loaded with dify_plugin's PluginRegistration, as the runtime does
22 passed              # 10 offline + 12 live against https://v2.convertapi.com

Live: provider validation (valid, regional and invalid token); DOCX/HTML → PDF and PDF/A;
PDF → DOCX; CSV → XLSX → PDF → XLSX (table values checked); merge 2 PDFs with bookmarks;
compress; PDF → JPG → PDF → OCR to text and searchable PDF; EU region; unsupported pair,
bad page range and bad JSON return readable errors.
```

The package was checked against the rules in langgenius/dify-marketplace-toolkit (contents, secrets, manifest fields, README sections, dependency pins, sensitive-capability patterns, PR body format).

## Reviewer notes

Tested with dify_plugin 0.11.0 through the SDK runtime and live ConvertAPI calls, not yet in a running Dify Community Edition or Dify Cloud instance.
