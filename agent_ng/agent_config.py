"""
Agent Configuration
==================

Central configuration file for the CMW Platform Agent.
Contains all configurable settings including refresh intervals, timeouts, and other parameters.
"""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env file before reading environment variables
# Find .env file relative to project root (parent of agent_ng directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

@dataclass
class RefreshIntervals:
    """Auto-refresh intervals for UI components"""
    interval: float = 15.0     # General UI refresh interval (seconds)
    iteration: float = 2.0     # Iteration/progress refresh interval (seconds)

@dataclass
class AgentSettings:
    """Main agent configuration settings"""
    # Language settings
    default_language: str = "ru"
    supported_languages: list = None

    # Port settings
    default_port: int = 7860
    auto_port_range: int = 10  # Number of ports to try when auto-finding

    # UI settings
    refresh_intervals: RefreshIntervals = None

    # Agent settings
    max_conversation_history: int = 50
    max_tokens_per_request: int = 4000
    request_timeout: float = 30.0

    # LLM provider/model settings
    default_provider: str = "mistral"
    default_model: str = None  # None means use first model (index 0)

    # Debug settings
    debug_mode: bool = False
    verbose_logging: bool = False

    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.supported_languages is None:
            self.supported_languages = ["en", "ru"]

        if self.refresh_intervals is None:
            self.refresh_intervals = RefreshIntervals()

class AgentConfig:
    """Central configuration manager for the CMW Platform Agent"""

    def __init__(self):
        self.settings = AgentSettings()
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Language settings - use GRADIO_DEFAULT_LANGUAGE for Gradio UI
        if os.getenv("GRADIO_DEFAULT_LANGUAGE"):
            self.settings.default_language = os.getenv("GRADIO_DEFAULT_LANGUAGE")

        # Port settings - use GRADIO_DEFAULT_PORT for Gradio server
        if os.getenv("GRADIO_DEFAULT_PORT"):
            try:
                self.settings.default_port = int(os.getenv("GRADIO_DEFAULT_PORT"))
            except ValueError as e:
                logging.warning(f"Invalid GRADIO_DEFAULT_PORT value, using default: {e}")

        # LLM provider/model settings
        if os.getenv("AGENT_PROVIDER"):
            self.settings.default_provider = os.getenv("AGENT_PROVIDER").strip()

        model_env = os.getenv("AGENT_DEFAULT_MODEL")
        if model_env and model_env.strip():
            self.settings.default_model = model_env.strip()

        # Debug settings
        if os.getenv("CMW_DEBUG_MODE", "").lower() in ["true", "1", "yes"]:
            self.settings.debug_mode = True

        if os.getenv("CMW_VERBOSE_LOGGING", "").lower() in ["true", "1", "yes"]:
            self.settings.verbose_logging = True

        # Refresh intervals from environment
        self._load_refresh_intervals_from_env()

    def _load_refresh_intervals_from_env(self):
        """Load refresh intervals from environment variables, if provided.

        Supported variables (seconds, float):
          - UI_REFRESH_INTERVAL          (general UI refresh)
          - ITERATION_REFRESH_INTERVAL   (progress/iteration refresh)

        Falls back to defaults when not set or invalid.
        """
        interval_val = os.getenv("UI_REFRESH_INTERVAL")
        if interval_val is not None:
            try:
                self.settings.refresh_intervals.interval = float(interval_val)
            except ValueError as e:
                logging.warning(f"Invalid UI_REFRESH_INTERVAL value, using default: {e}")

        iteration_val = os.getenv("ITERATION_REFRESH_INTERVAL")
        if iteration_val is not None:
            try:
                self.settings.refresh_intervals.iteration = float(iteration_val)
            except ValueError as e:
                logging.warning(f"Invalid ITERATION_REFRESH_INTERVAL value, using default: {e}")

    def get_refresh_intervals(self) -> RefreshIntervals:
        """Get the current refresh intervals configuration"""
        return self.settings.refresh_intervals

    def get_language_settings(self) -> dict[str, Any]:
        """Get language-related settings"""
        return {
            "default_language": self.settings.default_language,
            "supported_languages": self.settings.supported_languages
        }

    def get_port_settings(self) -> dict[str, Any]:
        """Get port-related settings"""
        return {
            "default_port": self.settings.default_port,
            "auto_port_range": self.settings.auto_port_range
        }

    def get_agent_settings(self) -> dict[str, Any]:
        """Get agent-related settings"""
        return {
            "max_conversation_history": self.settings.max_conversation_history,
            "max_tokens_per_request": self.settings.max_tokens_per_request,
            "request_timeout": self.settings.request_timeout
        }

    def get_llm_settings(self) -> dict[str, Any]:
        """Get LLM provider/model settings"""
        return {
            "default_provider": self.settings.default_provider,
            "default_model": self.settings.default_model
        }

    def get_debug_settings(self) -> dict[str, Any]:
        """Get debug-related settings"""
        return {
            "debug_mode": self.settings.debug_mode,
            "verbose_logging": self.settings.verbose_logging
        }

    def update_setting(self, category: str, key: str, value: Any):
        """Update a specific setting"""
        if category == "refresh_intervals":
            if hasattr(self.settings.refresh_intervals, key):
                setattr(self.settings.refresh_intervals, key, value)
        elif hasattr(self.settings, key):
            setattr(self.settings, key, value)

    def print_config(self):
        """Print current configuration"""
        print("Agent Configuration:")
        print(f"  Language: {self.settings.default_language}")
        print(f"  Port: {self.settings.default_port}")
        print(f"  Provider: {self.settings.default_provider}")
        if self.settings.default_model:
            print(f"  Model: {self.settings.default_model}")
        else:
            print("  Model: (default - first model)")
        print(f"  Debug Mode: {self.settings.debug_mode}")
        print(f"  Refresh Interval: {self.settings.refresh_intervals.interval}s")
        print(f"  Iteration Interval: {self.settings.refresh_intervals.iteration}s")

# Global configuration instance
config = AgentConfig()

# Convenience functions for easy access
def get_refresh_intervals() -> RefreshIntervals:
    """Get refresh intervals configuration"""
    return config.get_refresh_intervals()

def get_language_settings() -> dict[str, Any]:
    """Get language settings"""
    return config.get_language_settings()

def get_port_settings() -> dict[str, Any]:
    """Get port settings"""
    return config.get_port_settings()

def get_agent_settings() -> dict[str, Any]:
    """Get agent settings"""
    return config.get_agent_settings()

def get_debug_settings() -> dict[str, Any]:
    """Get debug settings"""
    return config.get_debug_settings()

def get_llm_settings() -> dict[str, Any]:
    """Get LLM provider/model settings"""
    return config.get_llm_settings()


def env_flag_true(name: str) -> bool:
    """Return True if ``name`` is set to a truthy token (1/true/yes/on)."""
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def get_ui_download_prep_after_stream() -> bool:
    """Run download-file preparation chained on streaming end.

    When ``False`` (default), Markdown/HTML/artifacts export refresh runs when opening
    the Downloads tab. Turning this on also refreshes downloads on streaming completion.

    Environment ``CMW_UI_DOWNLOAD_PREP_AFTER_STREAM``:
    ``1``/``true``/``yes``/``on`` to enable.
    """
    return env_flag_true("CMW_UI_DOWNLOAD_PREP_AFTER_STREAM")


def get_skills_dir() -> Path:
    """Return the directory where the agent looks for ``<name>/SKILL.md`` skills.

    Environment ``CMW_SKILLS_DIR`` overrides the default ``<repo>/.agents/skills``.
    The directory is allowed to be missing — the agent then behaves as if no
    skills are installed.
    """
    override = (os.getenv("CMW_SKILLS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    # <repo> is the parent of the agent_ng/ package.
    return (Path(__file__).parent.parent / ".agents" / "skills").resolve()


def get_skills_enabled() -> bool:
    """Master switch for the skill runtime.

    Environment ``CMW_SKILLS_ENABLED``: any non-truthy value (including the
    default absence of the variable) means skills are **enabled**; the variable
    is opt-out. Set ``CMW_SKILLS_ENABLED=false`` (or ``0``/``no``/``off``) to
    disable.
    """
    raw = (os.getenv("CMW_SKILLS_ENABLED") or "").strip().lower()
    if not raw:
        return True
    return raw not in ("0", "false", "no", "off")


def get_skill_max_body_chars() -> int:
    """Soft cap on a skill's body when loaded into context.

    Environment ``CMW_SKILL_MAX_BODY_CHARS``: integer, default ``60000``.
    """
    raw = (os.getenv("CMW_SKILL_MAX_BODY_CHARS") or "").strip()
    if not raw:
        return 60_000
    try:
        return int(raw)
    except ValueError as exc:
        logging.getLogger(__name__).warning(
            "Invalid CMW_SKILL_MAX_BODY_CHARS=%r, using default 60000: %s",
            raw,
            exc,
        )
        return 60_000
