from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tool_runtime import run_conversion


class MergePdfTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from run_conversion(
            self,
            tool_parameters,
            action="merge_pdf",
            source_format="pdf",
            target_format="merge",
            allowed_sources={"pdf"},
            file_parameter="input_files",
            multiple=True,
            min_files=2,
            field_mapping={"bookmarks": "BookmarksTableOfContents"},
        )
