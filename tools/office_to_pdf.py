from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tool_runtime import run_conversion


class OfficeToPdfTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from run_conversion(
            self,
            tool_parameters,
            action="office_to_pdf",
            target_format="pdf",
            allowed_sources={
                "doc", "docx", "docm", "dot", "dotx", "rtf", "odt", "txt", "wpd",
                "xls", "xlsx", "xlsm", "xlsb", "ods", "csv",
                "ppt", "pptx", "pptm", "pps", "ppsx", "odp",
                "html", "htm", "mhtml", "md", "vsd", "vsdx", "pub",
            },
            field_mapping={"pdfa": "Pdfa"} if tool_parameters.get("pdfa") else {},
        )
