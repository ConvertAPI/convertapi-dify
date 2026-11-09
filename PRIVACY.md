# ConvertAPI Dify Plugin Privacy Policy

Last updated: November 9, 2026 · Plugin version 0.1.0

This policy explains how the ConvertAPI plugin for Dify ("the plugin"), published by UAB ConvertAPI, handles data.

## What the plugin processes

- **Files you convert.** When a ConvertAPI tool runs, the plugin reads the input files from Dify and sends them over HTTPS to the ConvertAPI service for conversion. The converted files are returned to Dify as tool output.
- **Conversion settings.** Formats and options such as page ranges, OCR language, compression preset or a document's open password are sent with the request so ConvertAPI can perform the conversion.
- **Your API token.** Dify stores the token as an encrypted provider credential. The plugin sends it only to the ConvertAPI host of the region you choose, in the `Authorization` header, and never writes it to messages or logs.

## Where data is sent

Only to ConvertAPI: `v2.convertapi.com` by default, or the regional host you select (`eu-v2`, `uk-v2`, `us-v2`, `ca-v2`, `as-v2` or `au-v2` `.convertapi.com`). The plugin contacts no other third party.

## Storage and retention

- The plugin keeps no data of its own. It holds files in memory only while a tool runs.
- The plugin asks ConvertAPI to return results inline (`StoreFile=false`). In this mode ConvertAPI converts in memory and does not store input or output files.
- Dify stores tool inputs and outputs according to your Dify deployment's settings.

## What the plugin does not do

It collects no analytics or telemetry, does not profile users, and does not sell or share data.

## ConvertAPI service

ConvertAPI is ISO 27001 certified and SOC 2 Type II audited. Our privacy policy, DPA and security documents are available at https://www.convertapi.com/compliance, and our terms at https://www.convertapi.com/terms.

## Contact

UAB ConvertAPI · support@convertapi.com · https://www.convertapi.com
