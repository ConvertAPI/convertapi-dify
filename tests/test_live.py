"""Live tests against the production ConvertAPI service.

Run with CONVERTAPI_TOKEN_FILE=/path/to/token-file. Each test goes through the
tool classes exactly as Dify loads them, with Dify File objects as inputs.
Outputs are written to test-output/ for a manual look.
"""

import io
import json
import zipfile
from pathlib import Path

import pytest
import requests

from dify_plugin.entities.tool import ToolInvokeMessage, ToolRuntime
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.file.entities import FileType
from dify_plugin.file.file import File

OUT = Path(__file__).resolve().parent.parent / "test-output"
OUT.mkdir(exist_ok=True)
DEMO_DOCX = "https://cdn.convertapi.com/public/files/demo.docx"
CSV = b"Product,Quantity,Price\nWidget,12,3.50\nGadget,7,19.99\nGizmo,3,105.00\n"
HTML = b"<html><body><h1>Quarterly report</h1><p>Revenue grew in every region.</p></body></html>"

pytestmark = pytest.mark.usefixtures("token")


def dify_file(name: str, content: bytes, mime: str = "application/octet-stream") -> File:
    f = File(
        url="https://files.invalid/never-fetched",
        filename=name,
        extension="." + name.rsplit(".", 1)[-1],
        mime_type=mime,
        size=len(content),
        type=FileType.DOCUMENT,
    )
    f._blob = content  # the SDK would download it from Dify storage
    return f


def run(registration, token, tool: str, params: dict, region: str = "global"):
    cls = registration.get_tool_cls("convertapi", tool)
    instance = cls(
        runtime=ToolRuntime(credentials={"api_token": token, "region": region}, user_id="test", session_id="test"),
        session=None,
    )
    texts, jsons, blobs = [], [], []
    for msg in instance._invoke(params):
        if msg.type == ToolInvokeMessage.MessageType.TEXT:
            texts.append(msg.message.text)
        elif msg.type == ToolInvokeMessage.MessageType.JSON:
            jsons.append(msg.message.json_object)
        elif msg.type == ToolInvokeMessage.MessageType.BLOB:
            blobs.append((msg.meta["filename"], msg.meta["mime_type"], msg.message.blob))
    joined = " ".join(texts)
    assert token not in joined and token not in json.dumps(jsons)
    for name, _, data in blobs:
        (OUT / f"{tool}-{name}").write_bytes(data)
    return joined, jsons[0], blobs


def ok(result):
    text, summary, blobs = result
    assert summary["status"] == "success", text
    assert blobs, text
    return summary, blobs


@pytest.fixture(scope="module")
def demo_docx():
    response = requests.get(DEMO_DOCX, timeout=60)
    response.raise_for_status()
    return response.content


@pytest.fixture(scope="module")
def demo_pdf(registration, token, demo_docx):
    _, blobs = ok(run(registration, token, "office_to_pdf", {
        "input_file": dify_file("demo.docx", demo_docx)}))
    name, mime, data = blobs[0]
    assert name == "demo.pdf" and mime == "application/pdf" and data.startswith(b"%PDF")
    return data


@pytest.fixture(scope="module")
def table_pdf(registration, token):
    summary, blobs = ok(run(registration, token, "convert_file", {
        "input_file": dify_file("sales.csv", CSV, "text/csv"), "output_format": "XLSX"}))
    assert summary["output_format"] == "xlsx"
    xlsx = blobs[0][2]
    _, blobs = ok(run(registration, token, "office_to_pdf", {"input_file": dify_file("sales.xlsx", xlsx)}))
    return blobs[0][2]


def test_provider_validation(registration, token):
    provider = registration.get_tool_provider_cls("convertapi")()
    provider._validate_credentials({"api_token": token})
    provider._validate_credentials({"api_token": token, "region": "eu"})
    with pytest.raises(ToolProviderCredentialValidationError, match="rejected the token"):
        provider._validate_credentials({"api_token": "not-a-real-token"})


def test_office_to_pdf_docx(demo_pdf):
    assert len(demo_pdf) > 10_000


def test_office_to_pdf_html_and_pdfa(registration, token, demo_docx):
    _, blobs = ok(run(registration, token, "office_to_pdf", {"input_file": dify_file("report.html", HTML, "text/html")}))
    assert blobs[0][2].startswith(b"%PDF")
    _, blobs = ok(run(registration, token, "office_to_pdf", {
        "input_file": dify_file("demo.docx", demo_docx), "pdfa": True}))
    assert b"pdfaid" in blobs[0][2] or b"PDF/A" in blobs[0][2]


def test_office_to_pdf_rejects_other_types(registration, token):
    text, summary, blobs = run(registration, token, "office_to_pdf", {"input_file": dify_file("a.zip", b"PK..")})
    assert summary["status"] == "error" and not blobs and "this tool accepts" in text


def test_pdf_to_word(registration, token, demo_pdf):
    _, blobs = ok(run(registration, token, "pdf_to_word", {
        "input_file": dify_file("demo.pdf", demo_pdf, "application/pdf"), "page_range": "1-2"}))
    name, mime, data = blobs[0]
    assert name.endswith(".docx") and "wordprocessingml" in mime
    assert "word/document.xml" in zipfile.ZipFile(io.BytesIO(data)).namelist()


def test_pdf_to_excel(registration, token, table_pdf):
    _, blobs = ok(run(registration, token, "pdf_to_excel", {
        "input_file": dify_file("sales.pdf", table_pdf), "single_sheet": True}))
    book = zipfile.ZipFile(io.BytesIO(blobs[0][2]))
    xml = "".join(book.read(n).decode("utf-8", "ignore") for n in book.namelist() if n.startswith("xl/"))
    assert "Widget" in xml and "Gizmo" in xml


def test_merge_pdf(registration, token, demo_pdf, table_pdf):
    summary, blobs = ok(run(registration, token, "merge_pdf", {
        "input_files": [dify_file("demo.pdf", demo_pdf), dify_file("sales.pdf", table_pdf)],
        "bookmarks": "filename"}))
    assert len(blobs) == 1 and summary["output_format"] == "pdf"
    assert len(blobs[0][2]) > len(table_pdf)


def test_merge_needs_two_files(registration, token, demo_pdf):
    text, summary, _ = run(registration, token, "merge_pdf", {"input_files": [dify_file("demo.pdf", demo_pdf)]})
    assert summary["status"] == "error" and "at least 2" in text


def test_compress_pdf(registration, token, demo_pdf):
    _, blobs = ok(run(registration, token, "compress_pdf", {
        "input_file": dify_file("demo.pdf", demo_pdf), "preset": "text"}))
    assert blobs[0][2].startswith(b"%PDF") and len(blobs[0][2]) < len(demo_pdf)


def test_ocr_scanned_pdf(registration, token, demo_pdf):
    # Make an image-only PDF: page 1 to JPG, then JPG back to PDF.
    _, blobs = ok(run(registration, token, "convert_file", {
        "input_file": dify_file("demo.pdf", demo_pdf), "output_format": "jpg",
        "extra_parameters": '{"PageRange": "1"}'}))
    jpg = blobs[0][2]
    _, blobs = ok(run(registration, token, "convert_file", {
        "input_file": dify_file("page.jpg", jpg, "image/jpeg"), "output_format": "pdf"}))
    scanned = blobs[0][2]
    _, blobs = ok(run(registration, token, "ocr_pdf", {
        "input_file": dify_file("scan.pdf", scanned), "language": "en", "output_type": "txt"}))
    name, _, data = blobs[0]
    assert name.endswith(".txt")
    assert len(data.decode("utf-8", "ignore").split()) > 20
    _, blobs = ok(run(registration, token, "ocr_pdf", {"input_file": dify_file("scan.pdf", scanned)}))
    assert blobs[0][2].startswith(b"%PDF")


def test_regional_endpoint(registration, token):
    _, blobs = ok(run(registration, token, "convert_file", {
        "input_file": dify_file("sales.csv", CSV), "output_format": "pdf"}, region="eu"))
    assert blobs[0][2].startswith(b"%PDF")


def test_unsupported_pair_and_bad_parameter(registration, token, demo_pdf):
    text, summary, blobs = run(registration, token, "convert_file", {
        "input_file": dify_file("demo.pdf", demo_pdf), "output_format": "mp3"})
    assert summary["status"] == "error" and not blobs and "Unsupported conversion" in text
    assert "convertapi.com/api" in text
    text, summary, _ = run(registration, token, "pdf_to_word", {
        "input_file": dify_file("demo.pdf", demo_pdf), "page_range": "abc"})
    assert summary["status"] == "error", text
    text, summary, _ = run(registration, token, "convert_file", {
        "input_file": dify_file("demo.pdf", demo_pdf), "output_format": "docx", "extra_parameters": "{oops"})
    assert summary["status"] == "error" and "JSON object" in text
