"""Shared logic for the ConvertAPI tools.

Each tool module defines exactly one Tool subclass and calls run_conversion(),
so the Dify loader finds one tool class per file.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from convertapi_client import (
    ConversionResult,
    ConvertApiClient,
    ConvertApiError,
    InputFile,
    form_value,
    normalize_format,
    parse_parameters_json,
    read_dify_file,
)


def build_fields(tool_parameters: dict[str, Any], mapping: dict[str, str]) -> dict[str, str]:
    """Map Dify parameter names to ConvertAPI parameter names, skipping blanks.

    Extra parameters from the JSON field go first, so the dedicated fields win.
    """
    fields = parse_parameters_json(tool_parameters.get("extra_parameters"))
    for dify_name, api_name in mapping.items():
        value = tool_parameters.get(dify_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        fields[api_name] = form_value(value.strip() if isinstance(value, str) else value)
    return fields


def fail(action: str, message: str) -> ConvertApiError:
    """The error to raise, so Dify marks the tool node as failed (and an agent sees the message)."""
    return ConvertApiError(f"ConvertAPI {action} failed: {message}")


def emit_result(
    tool: Any,
    action: str,
    inputs: list[InputFile],
    source_format: str,
    target_format: str,
    result: ConversionResult,
) -> Generator[ToolInvokeMessage, None, None]:
    names = ", ".join(f.filename for f in result.files)
    if len(inputs) == 1:
        summary = f"Converted {inputs[0].filename} ({source_format.upper()}) to {names}."
    else:
        summary = f"Processed {len(inputs)} files into {names}."
    yield tool.create_text_message(summary)
    yield tool.create_json_message(
        {
            "status": "success",
            "action": action,
            "input_files": [f.filename for f in inputs],
            "input_format": source_format,
            "output_format": target_format,
            "conversion_cost": result.conversion_cost,
            "output_files": [
                {"filename": f.filename, "extension": f.extension, "size_bytes": f.size}
                for f in result.files
            ],
        }
    )
    for item in result.files:
        yield tool.create_blob_message(
            blob=item.content,
            meta={"mime_type": item.mime_type, "filename": item.filename},
        )


def run_conversion(
    tool: Any,
    tool_parameters: dict[str, Any],
    *,
    action: str,
    target_format: str,
    source_format: str = "",
    allowed_sources: set[str] | None = None,
    file_parameter: str = "input_file",
    multiple: bool = False,
    min_files: int = 1,
    field_mapping: dict[str, str] | None = None,
) -> Generator[ToolInvokeMessage, None, None]:
    try:
        raw = tool_parameters.get(file_parameter)
        if multiple:
            values = list(raw or []) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
            if len(values) < min_files:
                raise ConvertApiError(f"Provide at least {min_files} files.")
            inputs = [read_dify_file(v, file_parameter) for v in values]
        else:
            inputs = [read_dify_file(raw, file_parameter)]

        source = normalize_format(source_format) or inputs[0].extension
        if not source:
            raise ConvertApiError(
                f"Cannot tell the format of '{inputs[0].filename}'. Give the file an extension"
                " or set the input format."
            )
        if allowed_sources is not None:
            for item in inputs:
                fmt = normalize_format(source_format) or item.extension
                if fmt not in allowed_sources:
                    raise ConvertApiError(
                        f"'{item.filename}' is a {fmt.upper() or 'file with no extension'}; this tool accepts "
                        + ", ".join(sorted(s.upper() for s in allowed_sources))
                        + "."
                    )

        fields = build_fields(tool_parameters, field_mapping or {})
        client = ConvertApiClient(tool.runtime.credentials)
        result = client.convert(source, target_format, inputs, fields)
        yield from emit_result(tool, action, inputs, source, result.files[0].extension, result)
    except ConvertApiError as exc:
        raise fail(action, str(exc)) from None
    except Exception as exc:  # never leak details or credentials to the user
        raise fail(action, f"Unexpected error ({exc.__class__.__name__}).") from None
