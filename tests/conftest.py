# Import the SDK first: it gevent-monkey-patches ssl, as in the plugin runtime (main.py).
import dify_plugin  # noqa: F401  isort: skip

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def registration():
    """Load the plugin exactly as the Dify plugin runtime does (from the plugin root)."""
    from dify_plugin import DifyPluginEnv
    from dify_plugin.core.plugin_registration import PluginRegistration

    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        return PluginRegistration(DifyPluginEnv())
    finally:
        os.chdir(cwd)


class Secret(str):
    """A str whose repr never shows the value (pytest prints fixture values on failures)."""

    def __repr__(self) -> str:
        return "'***'"


@pytest.fixture(scope="session")
def token():
    """Read the token from a file named by CONVERTAPI_TOKEN_FILE; never print it."""
    path = os.environ.get("CONVERTAPI_TOKEN_FILE")
    if not path or not Path(path).is_file():
        pytest.skip("CONVERTAPI_TOKEN_FILE not set; live tests skipped")
    value = Path(path).read_text().strip()
    if not value:
        pytest.skip("token file is empty")
    return Secret(value)
