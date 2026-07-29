"""Platform credentials are no longer exposed by ConfigTab."""

import inspect

from agent_ng.tabs.config_tab import ConfigTab


def test_platform_configuration_helpers_are_absent():
    source = inspect.getsource(ConfigTab)

    assert "CMW_USE_DOTENV" not in source
    assert "CMW_BASE_URL" not in source
    assert "CMW_LOGIN" not in source
    assert "CMW_PASSWORD" not in source
    assert not hasattr(ConfigTab, "use_dotenv_for_platform")
    assert not hasattr(ConfigTab, "_session_config_payload")


