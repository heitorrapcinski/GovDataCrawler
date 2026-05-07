"""Unit tests for Docker Compose configuration validation.

Validates: Requirements 1.1, 1.2, 1.3, 1.5

Parses docker-compose.yml and programmatically verifies the container
architecture, network isolation, volume mounts, and health checks.
"""

from pathlib import Path

import pytest
import yaml

COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose_config():
    """Parse docker-compose.yml and return the configuration dict."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestComposeFileStructure:
    """Validate docker-compose.yml is valid YAML with expected top-level keys."""

    def test_compose_file_exists(self):
        assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"

    def test_compose_is_valid_yaml(self, compose_config):
        assert compose_config is not None
        assert isinstance(compose_config, dict)

    def test_compose_has_services(self, compose_config):
        assert "services" in compose_config
        assert isinstance(compose_config["services"], dict)

    def test_compose_has_networks(self, compose_config):
        assert "networks" in compose_config
        assert isinstance(compose_config["networks"], dict)

    def test_compose_has_volumes(self, compose_config):
        assert "volumes" in compose_config
        assert isinstance(compose_config["volumes"], dict)


class TestGraniteServiceNetworkIsolation:
    """Verify granite service has no default network attachment (Req 1.2, 1.5)."""

    def test_granite_service_exists(self, compose_config):
        assert "granite" in compose_config["services"]

    def test_granite_only_on_internal_network(self, compose_config):
        granite = compose_config["services"]["granite"]
        networks = granite.get("networks", [])
        assert "openclaws-internal" in networks
        assert "default" not in networks

    def test_granite_has_no_default_network(self, compose_config):
        """Granite must not be attached to the default bridge network."""
        granite = compose_config["services"]["granite"]
        networks = granite.get("networks", [])
        # Only openclaws-internal should be listed
        assert len(networks) == 1
        assert networks[0] == "openclaws-internal"


class TestOpenclawsServiceNetworks:
    """Verify openclaws service has both networks (Req 1.1, 1.3)."""

    def test_openclaws_service_exists(self, compose_config):
        assert "openclaws" in compose_config["services"]

    def test_openclaws_has_default_network(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        networks = openclaws.get("networks", [])
        assert "default" in networks

    def test_openclaws_has_internal_network(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        networks = openclaws.get("networks", [])
        assert "openclaws-internal" in networks

    def test_openclaws_has_exactly_two_networks(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        networks = openclaws.get("networks", [])
        assert len(networks) == 2


class TestInternalNetworkConfiguration:
    """Verify openclaws-internal network has internal: true (Req 1.2, 1.5)."""

    def test_internal_network_defined(self, compose_config):
        assert "openclaws-internal" in compose_config["networks"]

    def test_internal_network_is_internal(self, compose_config):
        network_config = compose_config["networks"]["openclaws-internal"]
        assert network_config.get("internal") is True


class TestDependsOnConfiguration:
    """Verify openclaws depends_on granite with condition service_healthy (Req 1.1)."""

    def test_openclaws_depends_on_granite(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        depends_on = openclaws.get("depends_on", {})
        assert "granite" in depends_on

    def test_depends_on_condition_service_healthy(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        depends_on = openclaws["depends_on"]
        granite_dep = depends_on["granite"]
        assert granite_dep.get("condition") == "service_healthy"


class TestGraniteHealthcheck:
    """Verify granite has a healthcheck configured (Req 1.5)."""

    def test_granite_has_healthcheck(self, compose_config):
        granite = compose_config["services"]["granite"]
        assert "healthcheck" in granite

    def test_granite_healthcheck_has_test(self, compose_config):
        granite = compose_config["services"]["granite"]
        healthcheck = granite["healthcheck"]
        assert "test" in healthcheck
        assert isinstance(healthcheck["test"], list)

    def test_granite_healthcheck_has_interval(self, compose_config):
        granite = compose_config["services"]["granite"]
        healthcheck = granite["healthcheck"]
        assert "interval" in healthcheck

    def test_granite_healthcheck_has_timeout(self, compose_config):
        granite = compose_config["services"]["granite"]
        healthcheck = granite["healthcheck"]
        assert "timeout" in healthcheck

    def test_granite_healthcheck_has_retries(self, compose_config):
        granite = compose_config["services"]["granite"]
        healthcheck = granite["healthcheck"]
        assert "retries" in healthcheck

    def test_granite_healthcheck_has_start_period(self, compose_config):
        granite = compose_config["services"]["granite"]
        healthcheck = granite["healthcheck"]
        assert "start_period" in healthcheck


class TestOpenclawsInteractiveMode:
    """Verify openclaws has stdin_open and tty enabled (Req 1.1)."""

    def test_openclaws_stdin_open(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        assert openclaws.get("stdin_open") is True

    def test_openclaws_tty(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        assert openclaws.get("tty") is True


class TestTargetVolumeReadOnly:
    """Verify target volume is read-only (:ro) (Req 1.1)."""

    def test_openclaws_has_volumes(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        assert "volumes" in openclaws
        assert len(openclaws["volumes"]) > 0

    def test_target_volume_is_read_only(self, compose_config):
        openclaws = compose_config["services"]["openclaws"]
        volumes = openclaws["volumes"]
        target_volumes = [v for v in volumes if "/app/target" in v]
        assert len(target_volumes) == 1
        assert target_volumes[0].endswith(":ro")
