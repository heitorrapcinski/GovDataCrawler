"""Property-based tests for OpenClaws configuration validation.

Feature: openclaws-ai-assistant
Property 1: Agent configuration validation round-trip
Property 2: Granite configuration validation round-trip

Validates: Requirements 8.1, 8.2, 8.5, 8.6, 7.2, 2.4
"""

import os
from unittest.mock import patch

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from openclaws.config import AgentConfig, ConfigValidationError, GraniteConfig


# =============================================================================
# Property 1: Agent configuration validation round-trip
# =============================================================================

# --- Strategies for valid AgentConfig values ---

# Valid target folder: string with at most 4096 characters
_valid_target_folder = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=("\x00",),
    ),
    min_size=1,
    max_size=4096,
)

# Valid granite endpoint: string with at most 2048 characters
_valid_granite_endpoint = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=("\x00",),
    ),
    min_size=1,
    max_size=2048,
)

# Valid health check interval: integer between 5 and 300
_valid_health_check_interval = st.integers(min_value=5, max_value=300)

# Valid log level: one of DEBUG, INFO, WARN, ERROR
_valid_log_level = st.sampled_from(["DEBUG", "INFO", "WARN", "ERROR"])

# --- Strategies for invalid AgentConfig values ---

# Invalid target folder: string exceeding 4096 characters (use integer-mapped length)
_invalid_target_folder_too_long = st.integers(
    min_value=4097, max_value=4200
).map(lambda n: "x" * n)

# Invalid granite endpoint: string exceeding 2048 characters (use integer-mapped length)
_invalid_granite_endpoint_too_long = st.integers(
    min_value=2049, max_value=2200
).map(lambda n: "h" * n)

# Invalid health check interval: not an integer
_invalid_health_check_not_int = st.text(
    alphabet=st.characters(whitelist_categories=("L", "P", "S")),
    min_size=1,
    max_size=20,
).filter(lambda s: not s.strip().lstrip("-").isdigit())

# Invalid health check interval: integer below minimum (5)
_invalid_health_check_below_min = st.integers(
    min_value=-1000, max_value=4
).map(str)

# Invalid health check interval: integer above maximum (300)
_invalid_health_check_above_max = st.integers(
    min_value=301, max_value=10000
).map(str)

# Invalid log level: not one of DEBUG, INFO, WARN, ERROR
_invalid_log_level = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=20,
).filter(lambda s: s.upper() not in {"DEBUG", "INFO", "WARN", "ERROR"})


@settings(max_examples=100, deadline=1000)
@given(
    target_folder=_valid_target_folder,
    granite_endpoint=_valid_granite_endpoint,
    health_check_interval=_valid_health_check_interval,
    log_level=_valid_log_level,
)
def test_valid_env_vars_produce_correct_agent_config(
    target_folder: str,
    granite_endpoint: str,
    health_check_interval: int,
    log_level: str,
) -> None:
    """Property 1: For any set of valid environment variable values for the
    OpenClaws Agent (target folder path <= 4096 chars, granite endpoint
    <= 2048 chars, health check interval as integer 5-300, log level as one
    of DEBUG/INFO/WARN/ERROR), parsing the environment SHALL produce an
    AgentConfig with those exact values.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {
        "OPENCLAWS_TARGET_FOLDER": target_folder,
        "OPENCLAWS_GRANITE_ENDPOINT": granite_endpoint,
        "OPENCLAWS_HEALTH_CHECK_INTERVAL": str(health_check_interval),
        "OPENCLAWS_LOG_LEVEL": log_level,
    }
    with patch.dict(os.environ, env, clear=True):
        config = AgentConfig.from_env()

    assert config.target_folder == target_folder
    assert config.granite_endpoint == granite_endpoint
    assert config.health_check_interval == health_check_interval
    assert config.log_level == log_level.upper()


@settings(
    max_examples=100,
    deadline=1000,
    suppress_health_check=[HealthCheck.large_base_example],
)
@given(target_folder=_invalid_target_folder_too_long)
def test_target_folder_exceeding_max_length_raises_validation_error(
    target_folder: str,
) -> None:
    """Property 1 (invalid path): For any target folder path exceeding 4096
    characters, parsing SHALL raise a validation error whose message contains
    the variable name, the invalid value, and the expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_TARGET_FOLDER": target_folder}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_TARGET_FOLDER"
            assert "OPENCLAWS_TARGET_FOLDER" in str(e)
            assert "4096" in str(e)


@settings(
    max_examples=100,
    deadline=1000,
    suppress_health_check=[HealthCheck.large_base_example],
)
@given(endpoint=_invalid_granite_endpoint_too_long)
def test_granite_endpoint_exceeding_max_length_raises_validation_error(
    endpoint: str,
) -> None:
    """Property 1 (invalid endpoint): For any granite endpoint exceeding 2048
    characters, parsing SHALL raise a validation error whose message contains
    the variable name, the invalid value, and the expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_GRANITE_ENDPOINT": endpoint}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_GRANITE_ENDPOINT"
            assert "OPENCLAWS_GRANITE_ENDPOINT" in str(e)
            assert "2048" in str(e)


@settings(max_examples=100, deadline=1000)
@given(interval=_invalid_health_check_not_int)
def test_health_check_interval_non_integer_raises_validation_error(
    interval: str,
) -> None:
    """Property 1 (invalid type): For any non-integer health check interval
    value, parsing SHALL raise a validation error whose message contains the
    variable name, the invalid value, and the expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": interval}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_HEALTH_CHECK_INTERVAL"
            assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(e)
            assert interval in str(e)
            assert "integer between 5 and 300" in str(e)


@settings(max_examples=100, deadline=1000)
@given(interval=_invalid_health_check_below_min)
def test_health_check_interval_below_min_raises_validation_error(
    interval: str,
) -> None:
    """Property 1 (below range): For any health check interval below 5,
    parsing SHALL raise a validation error whose message contains the
    variable name, the invalid value, and the expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": interval}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_HEALTH_CHECK_INTERVAL"
            assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(e)
            assert interval in str(e)
            assert "integer between 5 and 300" in str(e)


@settings(max_examples=100, deadline=1000)
@given(interval=_invalid_health_check_above_max)
def test_health_check_interval_above_max_raises_validation_error(
    interval: str,
) -> None:
    """Property 1 (above range): For any health check interval above 300,
    parsing SHALL raise a validation error whose message contains the
    variable name, the invalid value, and the expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": interval}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_HEALTH_CHECK_INTERVAL"
            assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(e)
            assert interval in str(e)
            assert "integer between 5 and 300" in str(e)


@settings(max_examples=100, deadline=1000)
@given(log_level=_invalid_log_level)
def test_invalid_log_level_raises_validation_error(
    log_level: str,
) -> None:
    """Property 1 (invalid log level): For any log level value that is not
    one of DEBUG/INFO/WARN/ERROR, parsing SHALL raise a validation error
    whose message contains the variable name, the invalid value, and the
    expected format.

    Feature: openclaws-ai-assistant, Property 1: Agent configuration validation round-trip

    **Validates: Requirements 8.1, 8.5, 7.2**
    """
    env = {"OPENCLAWS_LOG_LEVEL": log_level}
    with patch.dict(os.environ, env, clear=True):
        try:
            AgentConfig.from_env()
            assert False, "Expected ConfigValidationError was not raised"
        except ConfigValidationError as e:
            assert e.variable == "OPENCLAWS_LOG_LEVEL"
            assert "OPENCLAWS_LOG_LEVEL" in str(e)
            assert log_level in str(e)


# =============================================================================
# Property 2: Granite configuration validation round-trip
# =============================================================================

# --- Strategies for valid GraniteConfig values ---

_valid_model_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=("\x00",),
    ),
    min_size=1,
    max_size=256,
)

_valid_inference_port = st.integers(min_value=1, max_value=65535)

_valid_max_context_length = st.integers(min_value=512, max_value=131072)

_valid_temperature = st.floats(
    min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False
)

_valid_max_tokens = st.integers(min_value=1, max_value=8192)

_valid_top_p = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)

# --- Strategies for invalid GraniteConfig values ---

_invalid_inference_port_out_of_range = st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=65536),
)

_invalid_inference_port_not_int = st.text(
    alphabet=st.characters(whitelist_categories=("L", "P", "S")),
    min_size=1,
    max_size=10,
).filter(lambda s: not s.strip().lstrip("-").isdigit())

_invalid_max_context_length_out_of_range = st.one_of(
    st.integers(max_value=511),
    st.integers(min_value=131073),
)

_invalid_temperature_out_of_range = st.one_of(
    st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False).filter(
        lambda x: x < 0.0
    ),
    st.floats(min_value=2.01, allow_nan=False, allow_infinity=False).filter(
        lambda x: x > 2.0
    ),
)


def _is_float_str(s: str) -> bool:
    """Check if a string can be parsed as a float."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


_invalid_temperature_not_float = st.text(
    alphabet=st.characters(whitelist_categories=("L", "P", "S")),
    min_size=1,
    max_size=10,
).filter(lambda s: not _is_float_str(s))

_invalid_max_tokens_out_of_range = st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=8193),
)

_invalid_top_p_out_of_range = st.one_of(
    st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False).filter(
        lambda x: x < 0.0
    ),
    st.floats(min_value=1.01, allow_nan=False, allow_infinity=False).filter(
        lambda x: x > 1.0
    ),
)

_model_name_too_long = st.integers(min_value=257, max_value=350).map(
    lambda n: "m" * n
)


class TestGraniteConfigValidRoundTrip:
    """Property 2: Valid Granite configuration values produce correct GraniteConfig.

    **Validates: Requirements 8.2, 8.6, 2.4**
    """

    @settings(max_examples=100, deadline=1000)
    @given(
        model_name=_valid_model_name,
        inference_port=_valid_inference_port,
        max_context_length=_valid_max_context_length,
        temperature=_valid_temperature,
        max_tokens=_valid_max_tokens,
        top_p=_valid_top_p,
    )
    def test_valid_env_vars_produce_correct_granite_config(
        self,
        model_name: str,
        inference_port: int,
        max_context_length: int,
        temperature: float,
        max_tokens: int,
        top_p: float,
    ) -> None:
        """For any valid set of Granite env vars, from_env() produces a GraniteConfig
        with those exact values.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {
            "GRANITE_MODEL_NAME": model_name,
            "GRANITE_INFERENCE_PORT": str(inference_port),
            "GRANITE_MAX_CONTEXT_LENGTH": str(max_context_length),
            "GRANITE_TEMPERATURE": str(temperature),
            "GRANITE_MAX_TOKENS": str(max_tokens),
            "GRANITE_TOP_P": str(top_p),
        }

        with patch.dict(os.environ, env, clear=False):
            config = GraniteConfig.from_env()

        assert config.model_name == model_name
        assert config.inference_port == inference_port
        assert config.max_context_length == max_context_length
        assert config.temperature == temperature
        assert config.max_tokens == max_tokens
        assert config.top_p == top_p


class TestGraniteConfigInvalidValues:
    """Property 2: Invalid Granite configuration values raise validation errors.

    **Validates: Requirements 8.2, 8.6, 2.4**
    """

    @settings(max_examples=100, deadline=1000)
    @given(port=_invalid_inference_port_out_of_range)
    def test_invalid_inference_port_out_of_range_raises_error(self, port: int) -> None:
        """For any inference port outside 1-65535, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_INFERENCE_PORT": str(port)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for port={port}"
            except ConfigValidationError as e:
                assert "GRANITE_INFERENCE_PORT" in str(e)
                assert str(port) in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(port_str=_invalid_inference_port_not_int)
    def test_invalid_inference_port_not_integer_raises_error(
        self, port_str: str
    ) -> None:
        """For any non-integer inference port string, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_INFERENCE_PORT": port_str}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for port='{port_str}'"
            except ConfigValidationError as e:
                assert "GRANITE_INFERENCE_PORT" in str(e)
                assert port_str in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(ctx_len=_invalid_max_context_length_out_of_range)
    def test_invalid_max_context_length_raises_error(self, ctx_len: int) -> None:
        """For any max_context_length outside 512-131072, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MAX_CONTEXT_LENGTH": str(ctx_len)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, (
                    f"Expected ConfigValidationError for max_context_length={ctx_len}"
                )
            except ConfigValidationError as e:
                assert "GRANITE_MAX_CONTEXT_LENGTH" in str(e)
                assert str(ctx_len) in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(temp=_invalid_temperature_out_of_range)
    def test_invalid_temperature_out_of_range_raises_error(self, temp: float) -> None:
        """For any temperature outside 0.0-2.0, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_TEMPERATURE": str(temp)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, (
                    f"Expected ConfigValidationError for temperature={temp}"
                )
            except ConfigValidationError as e:
                assert "GRANITE_TEMPERATURE" in str(e)
                assert str(temp) in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(temp_str=_invalid_temperature_not_float)
    def test_invalid_temperature_not_float_raises_error(self, temp_str: str) -> None:
        """For any non-float temperature string, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_TEMPERATURE": temp_str}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, (
                    f"Expected ConfigValidationError for temperature='{temp_str}'"
                )
            except ConfigValidationError as e:
                assert "GRANITE_TEMPERATURE" in str(e)
                assert temp_str in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(tokens=_invalid_max_tokens_out_of_range)
    def test_invalid_max_tokens_out_of_range_raises_error(self, tokens: int) -> None:
        """For any max_tokens outside 1-8192, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MAX_TOKENS": str(tokens)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, (
                    f"Expected ConfigValidationError for max_tokens={tokens}"
                )
            except ConfigValidationError as e:
                assert "GRANITE_MAX_TOKENS" in str(e)
                assert str(tokens) in str(e)

    @settings(max_examples=100, deadline=1000)
    @given(top_p=_invalid_top_p_out_of_range)
    def test_invalid_top_p_out_of_range_raises_error(self, top_p: float) -> None:
        """For any top_p outside 0.0-1.0, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_TOP_P": str(top_p)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for top_p={top_p}"
            except ConfigValidationError as e:
                assert "GRANITE_TOP_P" in str(e)
                assert str(top_p) in str(e)

    @settings(
        max_examples=100,
        deadline=1000,
        suppress_health_check=[HealthCheck.large_base_example],
    )
    @given(model_name=_model_name_too_long)
    def test_model_name_too_long_raises_error(self, model_name: str) -> None:
        """For any model_name exceeding 256 characters, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MODEL_NAME": model_name}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, (
                    f"Expected ConfigValidationError for model_name length={len(model_name)}"
                )
            except ConfigValidationError as e:
                assert "GRANITE_MODEL_NAME" in str(e)
