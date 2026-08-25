"""Unit tests for iris_devtester/config/container_state.py."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from iris_devtester.config.container_state import (
    ContainerState,
    ContainerStatus,
    HealthStatus,
)

VALID_ID = "a" * 64


def make_state(**kwargs):
    defaults = dict(
        container_id=VALID_ID,
        container_name="test-iris",
        status=ContainerStatus.RUNNING,
        created_at=datetime(2025, 1, 1),
        image="intersystems/iris-community:latest",
    )
    defaults.update(kwargs)
    return ContainerState(**defaults)


def make_mock_container(
    status="running",
    health_status="none",
    started_at="2025-01-01T00:00:00",
    finished_at="0001-01-01T00:00:00Z",
    ports=None,
    labels=None,
):
    container = MagicMock()
    container.id = VALID_ID
    container.name = "test-iris"
    container.status = status
    container.attrs = {
        "Created": "2025-01-01T00:00:00",
        "State": {
            "StartedAt": started_at,
            "FinishedAt": finished_at,
            "Health": {"Status": health_status},
        },
        "NetworkSettings": {
            "Ports": ports or {},
        },
        "Config": {
            "Image": "intersystems/iris-community:latest",
            "Labels": labels or {},
        },
    }
    return container


class TestContainerStatusEnum:
    def test_creating(self):
        assert ContainerStatus.CREATING == "creating"

    def test_starting(self):
        assert ContainerStatus.STARTING == "starting"

    def test_running(self):
        assert ContainerStatus.RUNNING == "running"

    def test_healthy(self):
        assert ContainerStatus.HEALTHY == "healthy"

    def test_stopped(self):
        assert ContainerStatus.STOPPED == "stopped"

    def test_removing(self):
        assert ContainerStatus.REMOVING == "removing"


class TestHealthStatusEnum:
    def test_starting(self):
        assert HealthStatus.STARTING == "starting"

    def test_healthy(self):
        assert HealthStatus.HEALTHY == "healthy"

    def test_unhealthy(self):
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_none(self):
        assert HealthStatus.NONE == "none"


class TestContainerStateValidation:
    def test_valid_container_id(self):
        state = make_state()
        assert state.container_id == VALID_ID

    def test_short_container_id_raises(self):
        with pytest.raises(ValidationError):
            make_state(container_id="abc")

    def test_non_hex_container_id_raises(self):
        with pytest.raises(ValidationError):
            make_state(container_id="z" * 64)

    def test_missing_container_name_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            ContainerState(
                container_id=VALID_ID,
                status=ContainerStatus.RUNNING,
                created_at=datetime(2025, 1, 1),
                image="iris:latest",
            )

    def test_defaults(self):
        state = make_state()
        assert state.health_status == HealthStatus.NONE
        assert state.started_at is None
        assert state.finished_at is None
        assert state.ports == {}
        assert state.config_source is None


class TestContainerStateFromContainer:
    def test_running_status(self):
        container = make_mock_container(status="running")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.RUNNING

    def test_exited_status(self):
        container = make_mock_container(status="exited")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.STOPPED

    def test_created_status(self):
        container = make_mock_container(status="created")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.CREATING

    def test_restarting_status(self):
        container = make_mock_container(status="restarting")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.STARTING

    def test_dead_status(self):
        container = make_mock_container(status="dead")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.STOPPED

    def test_unknown_status_defaults_to_stopped(self):
        container = make_mock_container(status="unknown_xyz")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.STOPPED

    def test_running_plus_healthy_upgrades_to_healthy(self):
        container = make_mock_container(status="running", health_status="healthy")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.HEALTHY
        assert state.health_status == HealthStatus.HEALTHY

    def test_running_plus_unhealthy_stays_running(self):
        container = make_mock_container(status="running", health_status="unhealthy")
        state = ContainerState.from_container(container)
        assert state.status == ContainerStatus.RUNNING
        assert state.health_status == HealthStatus.UNHEALTHY

    def test_port_extraction(self):
        ports = {"1972/tcp": [{"HostPort": "1972"}], "52773/tcp": [{"HostPort": "52773"}]}
        container = make_mock_container(ports=ports)
        state = ContainerState.from_container(container)
        assert state.ports[1972] == 1972
        assert state.ports[52773] == 52773

    def test_empty_ports(self):
        container = make_mock_container(ports={})
        state = ContainerState.from_container(container)
        assert state.ports == {}

    def test_null_port_bindings_skipped(self):
        ports = {"1972/tcp": None}
        container = make_mock_container(ports=ports)
        state = ContainerState.from_container(container)
        assert 1972 not in state.ports

    def test_started_at_parsed(self):
        container = make_mock_container(started_at="2025-06-01T10:00:00")
        state = ContainerState.from_container(container)
        assert state.started_at == datetime(2025, 6, 1, 10, 0, 0)

    def test_zero_started_at_is_none(self):
        container = make_mock_container(started_at="0001-01-01T00:00:00Z")
        state = ContainerState.from_container(container)
        assert state.started_at is None

    def test_empty_started_at_is_none(self):
        container = make_mock_container(started_at="")
        state = ContainerState.from_container(container)
        assert state.started_at is None

    def test_finished_at_parsed(self):
        container = make_mock_container(
            finished_at="2025-06-01T12:00:00",
            started_at="2025-06-01T10:00:00",
        )
        state = ContainerState.from_container(container)
        assert state.finished_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_config_source_from_label(self):
        labels = {"iris-devtester.config.source": "/path/to/config.yaml"}
        container = make_mock_container(labels=labels)
        state = ContainerState.from_container(container)
        assert state.config_source is not None

    def test_default_config_source_label_ignored(self):
        labels = {"iris-devtester.config.source": "default"}
        container = make_mock_container(labels=labels)
        state = ContainerState.from_container(container)
        assert state.config_source is None

    def test_no_labels(self):
        container = make_mock_container(labels={})
        state = ContainerState.from_container(container)
        assert state.config_source is None

    def test_health_starting(self):
        container = make_mock_container(status="running", health_status="starting")
        state = ContainerState.from_container(container)
        assert state.health_status == HealthStatus.STARTING

    def test_health_unknown_defaults_to_none(self):
        container = make_mock_container(status="running", health_status="bogus")
        state = ContainerState.from_container(container)
        assert state.health_status == HealthStatus.NONE


class TestContainerStateMethods:
    def test_is_running_true_when_running(self):
        state = make_state(status=ContainerStatus.RUNNING)
        assert state.is_running() is True

    def test_is_running_true_when_healthy(self):
        state = make_state(
            status=ContainerStatus.HEALTHY, health_status=HealthStatus.HEALTHY
        )
        assert state.is_running() is True

    def test_is_running_false_when_stopped(self):
        state = make_state(status=ContainerStatus.STOPPED)
        assert state.is_running() is False

    def test_is_healthy_true(self):
        state = make_state(
            status=ContainerStatus.HEALTHY, health_status=HealthStatus.HEALTHY
        )
        assert state.is_healthy() is True

    def test_is_healthy_false_when_only_running(self):
        state = make_state(
            status=ContainerStatus.RUNNING, health_status=HealthStatus.HEALTHY
        )
        assert state.is_healthy() is False

    def test_is_healthy_false_when_unhealthy(self):
        state = make_state(
            status=ContainerStatus.HEALTHY, health_status=HealthStatus.UNHEALTHY
        )
        assert state.is_healthy() is False

    def test_get_uptime_seconds_none_when_stopped(self):
        state = make_state(status=ContainerStatus.STOPPED)
        assert state.get_uptime_seconds() is None

    def test_get_uptime_seconds_none_when_started_at_none(self):
        state = make_state(status=ContainerStatus.RUNNING, started_at=None)
        assert state.get_uptime_seconds() is None

    def test_get_uptime_seconds_positive_when_running(self):
        past = datetime(2020, 1, 1, 0, 0, 0)
        state = make_state(status=ContainerStatus.RUNNING, started_at=past)
        uptime = state.get_uptime_seconds()
        assert uptime is not None
        assert uptime > 0

    def test_format_uptime_not_running(self):
        state = make_state(status=ContainerStatus.STOPPED)
        assert state.format_uptime() == "Not running"

    def test_format_uptime_seconds_only(self):
        past = datetime(2020, 1, 1, 0, 0, 30)
        state = make_state(status=ContainerStatus.RUNNING, started_at=past)
        # Can't predict exact uptime, just verify it doesn't crash and returns a string
        result = state.format_uptime()
        assert isinstance(result, str)
        assert "s" in result or "m" in result or "h" in result

    def test_format_ports_none_when_empty(self):
        state = make_state(ports={})
        assert state.format_ports() == "None"

    def test_format_ports_single(self):
        state = make_state(ports={1972: 1972})
        assert state.format_ports() == "1972->1972"

    def test_format_ports_multiple_sorted(self):
        state = make_state(ports={52773: 52773, 1972: 1972})
        result = state.format_ports()
        assert result == "1972->1972, 52773->52773"

    def test_to_text_output_contains_name(self):
        state = make_state()
        output = state.to_text_output()
        assert "test-iris" in output

    def test_to_text_output_contains_status(self):
        state = make_state(status=ContainerStatus.RUNNING)
        output = state.to_text_output()
        assert "running" in output

    def test_to_text_output_contains_health(self):
        state = make_state()
        output = state.to_text_output()
        assert "none" in output

    def test_to_text_output_with_config_source(self):
        state = make_state(config_source=Path("/some/config.yaml"))
        output = state.to_text_output()
        assert "Config:" in output

    def test_to_json_output_keys(self):
        state = make_state()
        result = state.to_json_output()
        expected_keys = [
            "container_id",
            "container_name",
            "status",
            "health_status",
            "created_at",
            "started_at",
            "finished_at",
            "uptime_seconds",
            "ports",
            "image",
            "config_source",
        ]
        for key in expected_keys:
            assert key in result

    def test_to_json_output_values(self):
        state = make_state()
        result = state.to_json_output()
        assert result["container_name"] == "test-iris"
        assert result["status"] == "running"
        assert result["started_at"] is None
        assert result["finished_at"] is None
        assert result["config_source"] is None

    def test_to_json_output_with_started_at(self):
        dt = datetime(2025, 1, 1, 12, 0, 0)
        state = make_state(status=ContainerStatus.RUNNING, started_at=dt)
        result = state.to_json_output()
        assert result["started_at"] == dt.isoformat()

    def test_to_json_output_with_config_source(self):
        state = make_state(config_source=Path("/some/config.yaml"))
        result = state.to_json_output()
        assert result["config_source"] == "/some/config.yaml"
