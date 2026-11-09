from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tool_runtime import run_conversion


class PdfToExcelTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from run_conversion(
            self,
            tool_parameters,
            action="pdf_to_excel",
            target_format="xlsx",
            allowed_sources={"pdf"},
            field_mapping={"page_range": "PageRange", "single_sheet": "SingleSheet", "password": "Password"},
        )
