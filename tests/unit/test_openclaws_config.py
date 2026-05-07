"""Unit tests for openclaws.config module."""

import os
from unittest.mock import patch

import pytest

from openclaws.config import (
    AgentConfig,
    ConfigValidationError,
    GraniteConfig,
    load_and_validate_config,
)


class TestAgentConfigDefaults:
    """Test AgentConfig default values when env vars are unset."""

    def test_defaults_when_no_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()
        assert config.target_folder == "./target"
        assert config.granite_endpoint == "http://granite:8080"
        assert config.health_check_interval == 30
        assert config.log_level == "INFO"


class TestAgentConfigParsing:
    """Test AgentConfig.from_env() parsing valid values."""

    def test_parses_all_env_vars(self):
        env = {
            "OPENCLAWS_TARGET_FOLDER": "/data/contracts",
            "OPENCLAWS_GRANITE_ENDPOINT": "http://localhost:9090",
            "OPENCLAWS_HEALTH_CHECK_INTERVAL": "60",
            "OPENCLAWS_LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AgentConfig.from_env()
        assert config.target_folder == "/data/contracts"
        assert config.granite_endpoint == "http://localhost:9090"
        assert config.health_check_interval == 60
        assert config.log_level == "DEBUG"

    def test_log_level_case_insensitive(self):
        env = {"OPENCLAWS_LOG_LEVEL": "warn"}
        with patch.dict(os.environ, env, clear=True):
            config = AgentConfig.from_env()
        assert config.log_level == "WARN"

    def test_health_check_interval_min_boundary(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "5"}
        with patch.dict(os.environ, env, clear=True):
            config = AgentConfig.from_env()
        assert config.health_check_interval == 5

    def test_health_check_interval_max_boundary(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "300"}
        with patch.dict(os.environ, env, clear=True):
            config = AgentConfig.from_env()
        assert config.health_check_interval == 300


class TestAgentConfigValidation:
    """Test AgentConfig.from_env() validation errors."""

    def test_invalid_health_check_interval_not_integer(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "abc"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(exc_info.value)
        assert "abc" in str(exc_info.value)
        assert "integer between 5 and 300" in str(exc_info.value)

    def test_invalid_health_check_interval_below_min(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "4"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(exc_info.value)
        assert "4" in str(exc_info.value)

    def test_invalid_health_check_interval_above_max(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "301"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_HEALTH_CHECK_INTERVAL" in str(exc_info.value)
        assert "301" in str(exc_info.value)

    def test_invalid_log_level(self):
        env = {"OPENCLAWS_LOG_LEVEL": "VERBOSE"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_LOG_LEVEL" in str(exc_info.value)
        assert "VERBOSE" in str(exc_info.value)

    def test_target_folder_exceeds_max_length(self):
        env = {"OPENCLAWS_TARGET_FOLDER": "x" * 4097}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_TARGET_FOLDER" in str(exc_info.value)
        assert "4096" in str(exc_info.value)

    def test_granite_endpoint_exceeds_max_length(self):
        env = {"OPENCLAWS_GRANITE_ENDPOINT": "h" * 2049}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                AgentConfig.from_env()
        assert "OPENCLAWS_GRANITE_ENDPOINT" in str(exc_info.value)
        assert "2048" in str(exc_info.value)


class TestGraniteConfigDefaults:
    """Test GraniteConfig default values when env vars are unset."""

    def test_defaults_when_no_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            config = GraniteConfig.from_env()
        assert config.model_name == "ibm-granite/granite-3.1-8b-instruct"
        assert config.inference_port == 8080
        assert config.max_context_length == 4096
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.top_p == 0.95


class TestGraniteConfigParsing:
    """Test GraniteConfig.from_env() parsing valid values."""

    def test_parses_all_env_vars(self):
        env = {
            "GRANITE_MODEL_NAME": "custom-model",
            "GRANITE_INFERENCE_PORT": "9090",
            "GRANITE_MAX_CONTEXT_LENGTH": "8192",
            "GRANITE_TEMPERATURE": "1.5",
            "GRANITE_MAX_TOKENS": "4096",
            "GRANITE_TOP_P": "0.8",
        }
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.model_name == "custom-model"
        assert config.inference_port == 9090
        assert config.max_context_length == 8192
        assert config.temperature == 1.5
        assert config.max_tokens == 4096
        assert config.top_p == 0.8

    def test_inference_port_boundaries(self):
        env = {"GRANITE_INFERENCE_PORT": "1"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.inference_port == 1

        env = {"GRANITE_INFERENCE_PORT": "65535"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.inference_port == 65535

    def test_temperature_boundaries(self):
        env = {"GRANITE_TEMPERATURE": "0.0"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.temperature == 0.0

        env = {"GRANITE_TEMPERATURE": "2.0"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.temperature == 2.0

    def test_top_p_boundaries(self):
        env = {"GRANITE_TOP_P": "0.0"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.top_p == 0.0

        env = {"GRANITE_TOP_P": "1.0"}
        with patch.dict(os.environ, env, clear=True):
            config = GraniteConfig.from_env()
        assert config.top_p == 1.0


class TestGraniteConfigValidation:
    """Test GraniteConfig.from_env() validation errors."""

    def test_invalid_inference_port_not_integer(self):
        env = {"GRANITE_INFERENCE_PORT": "abc"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_INFERENCE_PORT" in str(exc_info.value)
        assert "abc" in str(exc_info.value)

    def test_invalid_inference_port_zero(self):
        env = {"GRANITE_INFERENCE_PORT": "0"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_INFERENCE_PORT" in str(exc_info.value)

    def test_invalid_inference_port_above_max(self):
        env = {"GRANITE_INFERENCE_PORT": "65536"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_INFERENCE_PORT" in str(exc_info.value)

    def test_invalid_temperature_above_max(self):
        env = {"GRANITE_TEMPERATURE": "2.1"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_TEMPERATURE" in str(exc_info.value)
        assert "2.1" in str(exc_info.value)

    def test_invalid_temperature_not_float(self):
        env = {"GRANITE_TEMPERATURE": "hot"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_TEMPERATURE" in str(exc_info.value)
        assert "hot" in str(exc_info.value)

    def test_invalid_max_context_length_below_min(self):
        env = {"GRANITE_MAX_CONTEXT_LENGTH": "511"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_MAX_CONTEXT_LENGTH" in str(exc_info.value)

    def test_invalid_max_context_length_above_max(self):
        env = {"GRANITE_MAX_CONTEXT_LENGTH": "131073"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_MAX_CONTEXT_LENGTH" in str(exc_info.value)

    def test_invalid_max_tokens_zero(self):
        env = {"GRANITE_MAX_TOKENS": "0"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_MAX_TOKENS" in str(exc_info.value)

    def test_invalid_max_tokens_above_max(self):
        env = {"GRANITE_MAX_TOKENS": "8193"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_MAX_TOKENS" in str(exc_info.value)

    def test_invalid_top_p_above_max(self):
        env = {"GRANITE_TOP_P": "1.1"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_TOP_P" in str(exc_info.value)

    def test_invalid_top_p_negative(self):
        env = {"GRANITE_TOP_P": "-0.1"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_TOP_P" in str(exc_info.value)

    def test_model_name_exceeds_max_length(self):
        env = {"GRANITE_MODEL_NAME": "m" * 257}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigValidationError) as exc_info:
                GraniteConfig.from_env()
        assert "GRANITE_MODEL_NAME" in str(exc_info.value)
        assert "256" in str(exc_info.value)


class TestLoadAndValidateConfig:
    """Test the load_and_validate_config convenience function."""

    def test_successful_load(self):
        with patch.dict(os.environ, {}, clear=True):
            agent_config, granite_config = load_and_validate_config()
        assert isinstance(agent_config, AgentConfig)
        assert isinstance(granite_config, GraniteConfig)

    def test_exits_on_invalid_agent_config(self):
        env = {"OPENCLAWS_HEALTH_CHECK_INTERVAL": "invalid"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                load_and_validate_config()
        assert exc_info.value.code == 1

    def test_exits_on_invalid_granite_config(self):
        env = {"GRANITE_INFERENCE_PORT": "99999"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                load_and_validate_config()
        assert exc_info.value.code == 1
