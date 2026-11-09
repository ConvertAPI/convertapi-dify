"""Offline checks: plugin loads like in Dify, parameters map correctly, errors read well."""

import json

import pytest

from convertapi_client import (
    ConvertApiClient,
    ConvertApiError,
    InputFile,
    normalize_format,
    parse_parameters_json,
)

TOOLS = [
    "convert_file",
    "office_to_pdf",
    "pdf_to_word",
    "pdf_to_excel",
    "merge_pdf",
    "compress_pdf",
    "ocr_pdf",
]


def test_plugin_loads_like_dify(registration):
    assert registration.configuration.name == "convertapi"
    assert registration.get_tool_provider_cls("convertapi") is not None
    provider = registration.tools_configuration[0]
    assert [t.identity.name for t in provider.tools] == TOOLS
    for name in TOOLS:
        assert registration.get_tool_cls("convertapi", name) is not None, name
    creds = {c.name: c for c in provider.credentials_schema}
    assert creds["api_token"].required is True
    assert creds["region"].default == "global"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def client(response, region="global"):
    session = FakeSession(response)
    return ConvertApiClient({"api_token": "secret-token-value", "region": region}, session), session


PDF = InputFile("a.pdf", b"%PDF-1.4", "application/pdf")


def test_request_shape_single_file():
    c, s = client(FakeResponse(200, {"ConversionCost": 1, "Files": [
        {"FileName": "a.docx", "FileExt": "docx", "FileSize": 3, "FileData": "YWJj"}]}))
    result = c.convert("PDF", ".docx", [PDF], {"PageRange": "1-2"})
    url, kwargs = s.calls[0]
    assert url == "https://v2.convertapi.com/convert/pdf/to/docx"
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token-value"
    assert kwargs["data"] == {"PageRange": "1-2", "StoreFile": "false"}
    assert kwargs["files"][0][0] == "File"
    assert result.files[0].content == b"abc" and result.conversion_cost == 1


def test_request_shape_merge_and_region():
    c, s = client(FakeResponse(200, {"Files": [{"FileName": "m.pdf", "FileData": "YQ=="}]}), "eu")
    c.convert("pdf", "merge", [PDF, PDF], {})
    url, kwargs = s.calls[0]
    assert url == "https://eu-v2.convertapi.com/convert/pdf/to/merge"
    assert [f[0] for f in kwargs["files"]] == ["Files[0]", "Files[1]"]


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (401, {"Code": 4013, "Message": "User credentials are invalid"}, "rejected the token"),
        (402, {"Code": 4020, "Message": "No conversions left"}, "no conversions left"),
        (404, None, "no converter for this format pair"),
        (400, {"Code": 4000, "Message": "Parameter validation error.",
               "InvalidParameters": {"PageRange": ["Bad range"]}}, "PageRange: Bad range"),
        (503, None, "server error"),
        (500, {"Code": 5001, "Message": "Conversion failed. Invalid pages range."}, "Check the file and the parameters"),
    ],
)
def test_error_messages(status, body, expected):
    c, _ = client(FakeResponse(status, body))
    with pytest.raises(ConvertApiError) as err:
        c.convert("pdf", "docx", [PDF])
    assert expected in str(err.value)
    assert "secret-token-value" not in str(err.value)


def test_missing_token_and_bad_region():
    with pytest.raises(ConvertApiError, match="token is missing"):
        ConvertApiClient({})
    with pytest.raises(ConvertApiError, match="Unknown region"):
        ConvertApiClient({"api_token": "x", "region": "mars"})


def test_format_and_extra_parameters_validation():
    assert normalize_format(" .DOCX ") == "docx"
    with pytest.raises(ConvertApiError):
        normalize_format("../etc")
    assert parse_parameters_json('{"PageRange": "1-3", "Pdfa": true, "Timeout": 60.0}') == {
        "PageRange": "1-3", "Pdfa": "true", "Timeout": "60"}
    for bad in ["[1]", "{not json", json.dumps({"Token": "x"}), json.dumps({"Files[0]": "x"})]:
        with pytest.raises(ConvertApiError):
            parse_parameters_json(bad)
