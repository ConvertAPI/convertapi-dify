from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from convertapi_client import ConvertApiClient, ConvertApiError


class ConvertApiProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            ConvertApiClient(credentials).validate_credentials()
        except ConvertApiError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from None
