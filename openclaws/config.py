"""Configuration management for OpenClaws AI Assistant.

Parses and validates environment variables for both the OpenClaws Agent
and the Granite Service, applying defaults and raising clear validation
errors when values are out of range or of incompatible type.
"""

import logging
import os
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when an environment variable contains an invalid value."""

    def __init__(self, variable: str, value: str, expected: str) -> None:
        self.variable = variable
        self.value = value
        self.expected = expected
        super().__init__(
            f"Invalid configuration: {variable}='{value}' — expected {expected}"
        )


def _parse_int(variable: str, raw: str, min_val: int, max_val: int) -> int:
    """Parse an integer environment variable within a valid range."""
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ConfigValidationError(
            variable, raw, f"integer between {min_val} and {max_val}"
        )
    if value < min_val or value > max_val:
        raise ConfigValidationError(
            variable, raw, f"integer between {min_val} and {max_val}"
        )
    return value


def _parse_float(variable: str, raw: str, min_val: float, max_val: float) -> float:
    """Parse a float environment variable within a valid range."""
    try:
        value = float(raw)
    except (ValueError, TypeError):
        raise ConfigValidationError(
            variable, raw, f"float between {min_val} and {max_val}"
        )
    if value < min_val or value > max_val:
        raise ConfigValidationError(
            variable, raw, f"float between {min_val} and {max_val}"
        )
    return value


def _parse_str(variable: str, raw: str, max_length: int) -> str:
    """Parse a string environment variable with a maximum length constraint."""
    if len(raw) > max_length:
        raise ConfigValidationError(
            variable, raw[:50] + "..." if len(raw) > 50 else raw,
            f"string with at most {max_length} characters"
        )
    return raw


_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}


@dataclass
class AgentConfig:
    """OpenClaws Agent configuration from environment variables."""

    target_folder: str = "./target"
    granite_endpoint: str = "http://granite:8080"
    health_check_interval: int = 30
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Parse and validate configuration from environment variables.

        Reads OPENCLAWS_TARGET_FOLDER, OPENCLAWS_GRANITE_ENDPOINT,
        OPENCLAWS_HEALTH_CHECK_INTERVAL, and OPENCLAWS_LOG_LEVEL.

        Returns a validated AgentConfig instance.
        Raises ConfigValidationError if any value is invalid.
        """
        config = cls()

        raw_target = os.environ.get("OPENCLAWS_TARGET_FOLDER")
        if raw_target is not None:
            config.target_folder = _parse_str(
                "OPENCLAWS_TARGET_FOLDER", raw_target, 4096
            )

        raw_endpoint = os.environ.get("OPENCLAWS_GRANITE_ENDPOINT")
        if raw_endpoint is not None:
            config.granite_endpoint = _parse_str(
                "OPENCLAWS_GRANITE_ENDPOINT", raw_endpoint, 2048
            )

        raw_interval = os.environ.get("OPENCLAWS_HEALTH_CHECK_INTERVAL")
        if raw_interval is not None:
            config.health_check_interval = _parse_int(
                "OPENCLAWS_HEALTH_CHECK_INTERVAL", raw_interval, 5, 300
            )

        raw_log_level = os.environ.get("OPENCLAWS_LOG_LEVEL")
        if raw_log_level is not None:
            upper = raw_log_level.upper()
            if upper not in _VALID_LOG_LEVELS:
                raise ConfigValidationError(
                    "OPENCLAWS_LOG_LEVEL",
                    raw_log_level,
                    f"one of {', '.join(sorted(_VALID_LOG_LEVELS))}",
                )
            config.log_level = upper

        return config


@dataclass
class GraniteConfig:
    """Granite Service configuration from environment variables."""

    model_name: str = "ibm-granite/granite-3.1-8b-instruct"
    inference_port: int = 8080
    max_context_length: int = 4096
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95

    @classmethod
    def from_env(cls) -> "GraniteConfig":
        """Parse and validate configuration from environment variables.

        Reads GRANITE_MODEL_NAME, GRANITE_INFERENCE_PORT,
        GRANITE_MAX_CONTEXT_LENGTH, GRANITE_TEMPERATURE,
        GRANITE_MAX_TOKENS, and GRANITE_TOP_P.

        Returns a validated GraniteConfig instance.
        Raises ConfigValidationError if any value is invalid.
        """
        config = cls()

        raw_model = os.environ.get("GRANITE_MODEL_NAME")
        if raw_model is not None:
            config.model_name = _parse_str("GRANITE_MODEL_NAME", raw_model, 256)

        raw_port = os.environ.get("GRANITE_INFERENCE_PORT")
        if raw_port is not None:
            config.inference_port = _parse_int(
                "GRANITE_INFERENCE_PORT", raw_port, 1, 65535
            )

        raw_context = os.environ.get("GRANITE_MAX_CONTEXT_LENGTH")
        if raw_context is not None:
            config.max_context_length = _parse_int(
                "GRANITE_MAX_CONTEXT_LENGTH", raw_context, 512, 131072
            )

        raw_temp = os.environ.get("GRANITE_TEMPERATURE")
        if raw_temp is not None:
            config.temperature = _parse_float(
                "GRANITE_TEMPERATURE", raw_temp, 0.0, 2.0
            )

        raw_max_tokens = os.environ.get("GRANITE_MAX_TOKENS")
        if raw_max_tokens is not None:
            config.max_tokens = _parse_int(
                "GRANITE_MAX_TOKENS", raw_max_tokens, 1, 8192
            )

        raw_top_p = os.environ.get("GRANITE_TOP_P")
        if raw_top_p is not None:
            config.top_p = _parse_float("GRANITE_TOP_P", raw_top_p, 0.0, 1.0)

        return config


def load_and_validate_config() -> tuple[AgentConfig, GraniteConfig]:
    """Load, validate, and log configuration from environment variables.

    On success, logs the active configuration at INFO level (excluding
    sensitive credentials) and returns both config objects.

    On failure, logs the validation error and exits with a non-zero status code.
    """
    try:
        agent_config = AgentConfig.from_env()
    except ConfigValidationError as e:
        logger.error("Agent configuration error: %s", e)
        sys.exit(1)

    try:
        granite_config = GraniteConfig.from_env()
    except ConfigValidationError as e:
        logger.error("Granite configuration error: %s", e)
        sys.exit(1)

    # Log active configuration at INFO level, excluding sensitive credentials
    logger.info("OpenClaws Agent configuration loaded successfully:")
    logger.info("  target_folder=%s", agent_config.target_folder)
    logger.info("  granite_endpoint=%s", agent_config.granite_endpoint)
    logger.info("  health_check_interval=%d", agent_config.health_check_interval)
    logger.info("  log_level=%s", agent_config.log_level)
    logger.info("Granite Service configuration loaded successfully:")
    logger.info("  model_name=%s", granite_config.model_name)
    logger.info("  inference_port=%d", granite_config.inference_port)
    logger.info("  max_context_length=%d", granite_config.max_context_length)
    logger.info("  temperature=%.2f", granite_config.temperature)
    logger.info("  max_tokens=%d", granite_config.max_tokens)
    logger.info("  top_p=%.2f", granite_config.top_p)

    return agent_config, granite_config
