"""Property-based tests for OpenClaws configuration validation.

Feature: openclaws-ai-assistant
Property 2: Granite configuration validation round-trip

Validates: Requirements 8.2, 8.6, 2.4
"""

import os
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from openclaws.config import ConfigValidationError, GraniteConfig


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

_valid_temperature = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)

_valid_max_tokens = st.integers(min_value=1, max_value=8192)

_valid_top_p = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


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
    st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False).filter(lambda x: x < 0.0),
    st.floats(min_value=2.01, allow_nan=False, allow_infinity=False).filter(lambda x: x > 2.0),
)

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
    st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False).filter(lambda x: x < 0.0),
    st.floats(min_value=1.01, allow_nan=False, allow_infinity=False).filter(lambda x: x > 1.0),
)

_model_name_too_long = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=257,
    max_size=300,
)


def _is_float_str(s: str) -> bool:
    """Check if a string can be parsed as a float."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


class TestGraniteConfigValidRoundTrip:
    """Property 2: Valid Granite configuration values produce correct GraniteConfig.

    **Validates: Requirements 8.2, 8.6, 2.4**
    """

    @settings(max_examples=100)
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

    @settings(max_examples=100)
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

    @settings(max_examples=100)
    @given(port_str=_invalid_inference_port_not_int)
    def test_invalid_inference_port_not_integer_raises_error(self, port_str: str) -> None:
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

    @settings(max_examples=100)
    @given(ctx_len=_invalid_max_context_length_out_of_range)
    def test_invalid_max_context_length_raises_error(self, ctx_len: int) -> None:
        """For any max_context_length outside 512-131072, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MAX_CONTEXT_LENGTH": str(ctx_len)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for max_context_length={ctx_len}"
            except ConfigValidationError as e:
                assert "GRANITE_MAX_CONTEXT_LENGTH" in str(e)
                assert str(ctx_len) in str(e)

    @settings(max_examples=100)
    @given(temp=_invalid_temperature_out_of_range)
    def test_invalid_temperature_out_of_range_raises_error(self, temp: float) -> None:
        """For any temperature outside 0.0-2.0, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_TEMPERATURE": str(temp)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for temperature={temp}"
            except ConfigValidationError as e:
                assert "GRANITE_TEMPERATURE" in str(e)
                assert str(temp) in str(e)

    @settings(max_examples=100)
    @given(temp_str=_invalid_temperature_not_float)
    def test_invalid_temperature_not_float_raises_error(self, temp_str: str) -> None:
        """For any non-float temperature string, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_TEMPERATURE": temp_str}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for temperature='{temp_str}'"
            except ConfigValidationError as e:
                assert "GRANITE_TEMPERATURE" in str(e)
                assert temp_str in str(e)

    @settings(max_examples=100)
    @given(tokens=_invalid_max_tokens_out_of_range)
    def test_invalid_max_tokens_out_of_range_raises_error(self, tokens: int) -> None:
        """For any max_tokens outside 1-8192, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MAX_TOKENS": str(tokens)}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for max_tokens={tokens}"
            except ConfigValidationError as e:
                assert "GRANITE_MAX_TOKENS" in str(e)
                assert str(tokens) in str(e)

    @settings(max_examples=100)
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

    @settings(max_examples=100)
    @given(model_name=_model_name_too_long)
    def test_model_name_too_long_raises_error(self, model_name: str) -> None:
        """For any model_name exceeding 256 characters, from_env() raises ConfigValidationError.

        Feature: openclaws-ai-assistant, Property 2: Granite configuration validation round-trip
        """
        env = {"GRANITE_MODEL_NAME": model_name}

        with patch.dict(os.environ, env, clear=False):
            try:
                GraniteConfig.from_env()
                assert False, f"Expected ConfigValidationError for model_name length={len(model_name)}"
            except ConfigValidationError as e:
                assert "GRANITE_MODEL_NAME" in str(e)
