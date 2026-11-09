"""Small ConvertAPI REST client used by the Dify tools.

It calls https://v2.convertapi.com (or a regional endpoint) with the user's API
token, sends the input files as multipart form data and returns the converted
files in memory (StoreFile=false), so nothing is kept on ConvertAPI's side.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from typing import Any

import requests

REGION_BASE_URLS = {
    "global": "https://v2.convertapi.com",
    "eu": "https://eu-v2.convertapi.com",
    "uk": "https://uk-v2.convertapi.com",
    "us": "https://us-v2.convertapi.com",
    "ca": "https://ca-v2.convertapi.com",
    "as": "https://as-v2.convertapi.com",
    "au": "https://au-v2.convertapi.com",
}

CONNECT_TIMEOUT_SECONDS = 15
# ConvertAPI's own conversion timeout defaults to 900 s for the largest jobs.
READ_TIMEOUT_SECONDS = 960
USER_AGENT = "ConvertAPI-Dify-Plugin/0.1.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]{1,20}$")


class ConvertApiError(Exception):
    """An error with a message that is safe to show to the user."""


@dataclass
class InputFile:
    filename: str
    content: bytes
    mime_type: str

    @property
    def extension(self) -> str:
        return os.path.splitext(self.filename)[1].lstrip(".").lower()


@dataclass
class OutputFile:
    filename: str
    extension: str
    size: int
    content: bytes

    @property
    def mime_type(self) -> str:
        return mimetypes.guess_type(self.filename)[0] or "application/octet-stream"


@dataclass
class ConversionResult:
    files: list[OutputFile]
    conversion_cost: int | None


def normalize_format(value: Any) -> str:
    """Turn '.DOCX', ' docx ' or 'DOCX' into 'docx'; validate the shape."""
    text = str(value or "").strip().lower().lstrip(".")
    if not text:
        return ""
    if not FORMAT_PATTERN.match(text):
        raise ConvertApiError(
            f"'{value}' is not a valid file format. Use a short extension such as pdf, docx or png."
        )
    return text


def resolve_base_url(credentials: dict[str, Any]) -> str:
    region = str(credentials.get("region") or "global").strip().lower()
    if region not in REGION_BASE_URLS:
        raise ConvertApiError(
            f"Unknown region '{region}'. Choose one of: {', '.join(REGION_BASE_URLS)}."
        )
    return REGION_BASE_URLS[region]


def read_dify_file(value: Any, label: str = "input_file") -> InputFile:
    """Read a Dify file object (or the first one of a list) into memory."""
    if isinstance(value, (list, tuple)):
        if not value:
            raise ConvertApiError(f"{label} is required.")
        value = value[0]
    if value is None:
        raise ConvertApiError(f"{label} is required.")

    filename = str(getattr(value, "filename", None) or "").strip()
    extension = str(getattr(value, "extension", None) or "").strip()
    if not filename:
        filename = "file" + (extension if extension.startswith(".") or not extension else "." + extension)
    elif extension and not os.path.splitext(filename)[1]:
        filename += extension if extension.startswith(".") else "." + extension

    try:
        content = value.blob
    except Exception as exc:  # the SDK downloads the file from Dify storage here
        raise ConvertApiError(
            f"Could not read '{filename}' from Dify file storage ({exc.__class__.__name__}). On self-hosted Dify,"
            " the plugin daemon must reach the Dify API: set INTERNAL_FILES_URL (for Docker Compose,"
            " INTERNAL_FILES_URL=http://api:5001) and restart Dify."
        ) from None
    if not content:
        raise ConvertApiError(f"'{filename}' is empty.")

    mime_type = (
        str(getattr(value, "mime_type", None) or "").strip()
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    return InputFile(filename=filename, content=content, mime_type=mime_type)


def parse_parameters_json(raw: Any) -> dict[str, str]:
    """Parse the optional 'extra parameters' JSON object into form fields."""
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConvertApiError(
            f"Extra parameters must be a JSON object, for example {{\"PageRange\": \"1-3\"}}. {exc.msg}."
        ) from exc
    if not isinstance(data, dict):
        raise ConvertApiError(
            "Extra parameters must be a JSON object, for example {\"PageRange\": \"1-3\"}."
        )
    blocked = {"file", "files", "secret", "token", "storefile"}
    fields: dict[str, str] = {}
    for key, val in data.items():
        name = str(key).strip()
        if name.lower() in blocked or name.lower().startswith("files["):
            raise ConvertApiError(f"'{name}' cannot be set in the extra parameters.")
        if val is None:
            continue
        fields[name] = form_value(val)
    return fields


def form_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


class ConvertApiClient:
    def __init__(self, credentials: dict[str, Any], session: requests.Session | None = None):
        token = str(credentials.get("api_token") or "").strip()
        if not token:
            raise ConvertApiError(
                "The ConvertAPI token is missing. Add it in the plugin's authorization settings."
            )
        self._token = token
        self.base_url = resolve_base_url(credentials)
        self._session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

    def validate_credentials(self) -> None:
        """Check the token with a request that costs no conversions."""
        try:
            response = self._session.get(
                f"{self.base_url}/user",
                headers=self._headers(),
                timeout=(CONNECT_TIMEOUT_SECONDS, 30),
            )
        except requests.RequestException as exc:
            raise ConvertApiError(f"Could not reach ConvertAPI at {self.base_url}: {exc.__class__.__name__}.") from exc
        if response.status_code == 401:
            raise ConvertApiError(
                "ConvertAPI rejected the token. Copy an API token from https://www.convertapi.com/a/auth and try again."
            )
        if response.status_code >= 400:
            raise self._error_from_response(response, "validate the token")

    def convert(
        self,
        source_format: str,
        target_format: str,
        files: list[InputFile],
        parameters: dict[str, str] | None = None,
    ) -> ConversionResult:
        source_format = normalize_format(source_format)
        target_format = normalize_format(target_format)
        if not source_format:
            raise ConvertApiError("The input format is unknown. Give the file an extension or set the input format.")
        if not target_format:
            raise ConvertApiError("The output format is required, for example pdf or docx.")
        if not files:
            raise ConvertApiError("At least one input file is required.")

        fields = dict(parameters or {})
        fields["StoreFile"] = "false"
        if len(files) == 1:
            multipart = [("File", (files[0].filename, files[0].content, files[0].mime_type))]
        else:
            multipart = [
                (f"Files[{index}]", (item.filename, item.content, item.mime_type))
                for index, item in enumerate(files)
            ]

        url = f"{self.base_url}/convert/{source_format}/to/{target_format}"
        try:
            response = self._session.post(
                url,
                headers=self._headers(),
                data=fields,
                files=multipart,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            )
        except requests.Timeout as exc:
            raise ConvertApiError(
                "ConvertAPI did not answer in time. Try a smaller file or a narrower page range."
            ) from exc
        except requests.RequestException as exc:
            raise ConvertApiError(f"Could not reach ConvertAPI at {self.base_url}: {exc.__class__.__name__}.") from exc

        if response.status_code >= 400:
            raise self._error_from_response(
                response, f"convert {source_format.upper()} to {target_format.upper()}"
            )
        return self._parse_result(response)

    @staticmethod
    def _parse_result(response: requests.Response) -> ConversionResult:
        try:
            body = response.json()
        except ValueError as exc:
            raise ConvertApiError("ConvertAPI returned a response that is not JSON.") from exc
        output: list[OutputFile] = []
        for item in body.get("Files") or []:
            data = item.get("FileData")
            if not data:
                raise ConvertApiError("ConvertAPI returned a file without content.")
            content = base64.b64decode(data)
            name = item.get("FileName") or "output"
            output.append(
                OutputFile(
                    filename=name,
                    extension=str(item.get("FileExt") or os.path.splitext(name)[1].lstrip(".")).lower(),
                    size=int(item.get("FileSize") or len(content)),
                    content=content,
                )
            )
        if not output:
            raise ConvertApiError("ConvertAPI returned no files.")
        cost = body.get("ConversionCost")
        return ConversionResult(files=output, conversion_cost=int(cost) if cost is not None else None)

    @staticmethod
    def _error_from_response(response: requests.Response, action: str) -> ConvertApiError:
        status = response.status_code
        message = ""
        details = ""
        try:
            body = response.json()
            message = str(body.get("Message") or "").strip()
            invalid = body.get("InvalidParameters")
            if isinstance(invalid, dict) and invalid:
                details = "; ".join(
                    f"{name}: {' '.join(map(str, errors)) if isinstance(errors, list) else errors}"
                    for name, errors in invalid.items()
                )
        except ValueError:
            pass

        if status == 401:
            hint = "ConvertAPI rejected the token. Check the API token in the plugin's authorization settings."
        elif status == 402:
            hint = "Your ConvertAPI account has no conversions left. Top up or upgrade at https://www.convertapi.com/a/billing."
        elif status == 404:
            hint = (
                "ConvertAPI has no converter for this format pair. "
                "See the supported conversions at https://www.convertapi.com/api."
            )
        elif status == 413:
            hint = "The file is too large for ConvertAPI."
        elif status == 429:
            hint = "Too many requests at once. Wait a moment and try again."
        elif status >= 500 and message.lower().startswith("conversion failed"):
            # ConvertAPI answers 500 with code 5001 when the file or a parameter cannot be converted.
            hint = "Check the file and the parameters, such as the page range."
        elif status >= 500:
            hint = "ConvertAPI had a server error. Try again in a minute."
        else:
            hint = ""
        if "unsupported conversion" in f"{message} {details}".lower():
            hint = "See the supported conversions at https://www.convertapi.com/api."

        parts = [f"Could not {action} (HTTP {status})."]
        if message:
            parts.append(message.rstrip(".") + ".")
        if details:
            parts.append(f"Invalid parameters: {details.rstrip('.')}.")
        if hint and hint not in parts:
            parts.append(hint)
        return ConvertApiError(" ".join(parts))
