from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tool_runtime import run_conversion


class ConvertFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from run_conversion(
            self,
            tool_parameters,
            action="convert_file",
            source_format=tool_parameters.get("input_format") or "",
            target_format=tool_parameters.get("output_format") or "",
        )
