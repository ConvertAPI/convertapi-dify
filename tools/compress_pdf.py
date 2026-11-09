from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tool_runtime import run_conversion


class CompressPdfTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from run_conversion(
            self,
            tool_parameters,
            action="compress_pdf",
            target_format="compress",
            allowed_sources={"pdf"},
            field_mapping={"preset": "Preset", "password": "Password"},
        )
