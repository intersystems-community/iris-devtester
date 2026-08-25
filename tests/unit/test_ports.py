"""Unit tests for iris_devtester ports module (registry, assignment, exceptions)."""

import errno
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# PortAssignment
# ---------------------------------------------------------------------------


class TestPortAssignment:
    def test_to_dict_round_trips_through_from_dict(self):
        from iris_devtester.ports.assignment import PortAssignment

        now = datetime(2025, 1, 15, 10, 30, 0)
        pa = PortAssignment(
            project_path="/home/tom/project",
            port=1972,
            assigned_at=now,
            assignment_type="auto",
            status="active",
            container_name="iris_db",
        )
        d = pa.to_dict()
        restored = PortAssignment.from_dict(d)

        assert restored.project_path == pa.project_path
        assert restored.port == pa.port
        assert restored.assignment_type == pa.assignment_type
        assert restored.status == pa.status
        assert restored.container_name == pa.container_name

    def test_container_name_defaults_to_none(self):
        from iris_devtester.ports.assignment import PortAssignment

        pa = PortAssignment(
            project_path="/p",
            port=1972,
            assigned_at=datetime.now(),
            assignment_type="auto",
            status="active",
        )
        assert pa.container_name is None

    def test_to_dict_includes_container_name_none(self):
        from iris_devtester.ports.assignment import PortAssignment

        pa = PortAssignment(
            project_path="/p",
            port=1972,
            assigned_at=datetime.now(),
            assignment_type="manual",
            status="active",
        )
        d = pa.to_dict()
        assert "container_name" in d
        assert d["container_name"] is None

    def test_from_dict_handles_missing_container_name(self):
        from iris_devtester.ports.assignment import PortAssignment

        now = datetime(2025, 1, 15, 10, 0, 0)
        d = {
            "project_path": "/p",
            "port": 1980,
            "assigned_at": now.isoformat(),
            "assignment_type": "auto",
            "status": "stale",
        }
        pa = PortAssignment.from_dict(d)
        assert pa.container_name is None
        assert pa.status == "stale"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestPortExceptions:
    def test_port_exhausted_error_message_contains_range(self):
        from iris_devtester.ports.exceptions import PortExhaustedError

        err = PortExhaustedError(port_range=(1972, 1975), current_assignments=[])
        msg = str(err)
        assert "1972" in msg
        assert "1975" in msg

    def test_port_exhausted_error_message_contains_project_paths(self):
        from iris_devtester.ports.assignment import PortAssignment
        from iris_devtester.ports.exceptions import PortExhaustedError

        pa = PortAssignment(
            project_path="/home/tom/myproject",
            port=1972,
            assigned_at=datetime.now(),
            assignment_type="auto",
            status="active",
        )
        err = PortExhaustedError(port_range=(1972, 1972), current_assignments=[pa])
        assert "/home/tom/myproject" in str(err)

    def test_port_exhausted_error_stores_attributes(self):
        from iris_devtester.ports.exceptions import PortExhaustedError

        err = PortExhaustedError(port_range=(1972, 1975), current_assignments=[])
        assert err.port_range == (1972, 1975)
        assert err.current_assignments == []

    def test_port_conflict_error_message_contains_project_paths_and_port(self):
        from iris_devtester.ports.exceptions import PortConflictError

        err = PortConflictError(
            requested_port=1972,
            requested_project="/home/tom/new",
            existing_project="/home/tom/old",
            existing_assignment_type="auto",
            existing_status="active",
        )
        msg = str(err)
        assert "1972" in msg
        assert "/home/tom/new" in msg
        assert "/home/tom/old" in msg

    def test_port_conflict_error_stores_attributes(self):
        from iris_devtester.ports.exceptions import PortConflictError

        err = PortConflictError(
            requested_port=1980,
            requested_project="/a",
            existing_project="/b",
            existing_assignment_type="manual",
            existing_status="active",
        )
        assert err.requested_port == 1980
        assert err.requested_project == "/a"
        assert err.existing_project == "/b"

    def test_port_assignment_timeout_error_message_contains_paths(self):
        from iris_devtester.ports.exceptions import PortAssignmentTimeoutError

        err = PortAssignmentTimeoutError(
            registry_path="/home/tom/.iris-devtester/registry.json",
            lock_path="/home/tom/.iris-devtester/registry.lock",
            timeout_seconds=5,
        )
        msg = str(err)
        assert "registry.json" in msg
        assert "registry.lock" in msg
        assert "5" in msg

    def test_port_assignment_timeout_error_stores_attributes(self):
        from iris_devtester.ports.exceptions import PortAssignmentTimeoutError

        err = PortAssignmentTimeoutError(
            registry_path="/reg",
            lock_path="/lock",
            timeout_seconds=10,
        )
        assert err.registry_path == "/reg"
        assert err.lock_path == "/lock"
        assert err.timeout_seconds == 10


# ---------------------------------------------------------------------------
# Helpers for registry tests
# ---------------------------------------------------------------------------


def make_registry(port_range=(19800, 19810)):
    """Create a PortRegistry backed by a temp directory."""
    from iris_devtester.ports.registry import PortRegistry

    tmpdir = tempfile.mkdtemp()
    reg_path = Path(tmpdir) / "registry.json"
    # Patch _is_host_port_free and _get_docker_bound_ports for isolation
    registry = PortRegistry(registry_path=reg_path, port_range=port_range)
    return registry, tmpdir


def free_port_side_effect(port):
    """Always says ports are free."""
    return True


# ---------------------------------------------------------------------------
# PortRegistry init
# ---------------------------------------------------------------------------


class TestPortRegistryInit:
    def test_creates_registry_file_when_missing(self):
        from iris_devtester.ports.registry import PortRegistry

        with tempfile.TemporaryDirectory() as tmpdir:
            reg_path = Path(tmpdir) / "registry.json"
            assert not reg_path.exists()
            PortRegistry(registry_path=reg_path)
            assert reg_path.exists()
            data = json.loads(reg_path.read_text())
            assert data["schema_version"] == "1.0"
            assert data["assignments"] == []

    def test_uses_custom_registry_path(self):
        from iris_devtester.ports.registry import PortRegistry

        with tempfile.TemporaryDirectory() as tmpdir:
            reg_path = Path(tmpdir) / "custom.json"
            r = PortRegistry(registry_path=reg_path)
            assert r.registry_path == reg_path

    def test_custom_port_range_stored(self):
        from iris_devtester.ports.registry import PortRegistry

        with tempfile.TemporaryDirectory() as tmpdir:
            reg_path = Path(tmpdir) / "r.json"
            r = PortRegistry(registry_path=reg_path, port_range=(5000, 5010))
            assert r.min_port == 5000
            assert r.max_port == 5010
            assert r.port_range == (5000, 5010)

    def test_does_not_overwrite_existing_registry(self):
        from iris_devtester.ports.registry import PortRegistry

        with tempfile.TemporaryDirectory() as tmpdir:
            reg_path = Path(tmpdir) / "r.json"
            # Pre-seed with data
            existing = {"schema_version": "1.0", "assignments": [{"project_path": "/x", "port": 19800, "assigned_at": datetime.now().isoformat(), "assignment_type": "auto", "status": "active", "container_name": None}]}
            reg_path.write_text(json.dumps(existing))
            PortRegistry(registry_path=reg_path)
            data = json.loads(reg_path.read_text())
            assert len(data["assignments"]) == 1


# ---------------------------------------------------------------------------
# PortRegistry assign_port
# ---------------------------------------------------------------------------


class TestPortRegistryAssign:
    def _make_registry(self, port_range=(19800, 19810)):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        r = PortRegistry(registry_path=reg_path, port_range=port_range)
        return r

    def test_auto_assigns_first_available_port(self):
        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            a = r.assign_port("/home/tom/project-a")
        assert a.port == 19800
        assert a.assignment_type == "auto"
        assert a.status == "active"

    def test_idempotent_returns_same_assignment(self):
        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            a1 = r.assign_port("/home/tom/project-a")
            a2 = r.assign_port("/home/tom/project-a")
        assert a1.port == a2.port

    def test_manual_assignment_uses_preferred_port(self):
        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            a = r.assign_port("/home/tom/project-b", preferred_port=19805)
        assert a.port == 19805
        assert a.assignment_type == "manual"

    def test_conflict_on_preferred_port_raises_when_no_fallback(self):
        from iris_devtester.ports.exceptions import PortConflictError

        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a", preferred_port=19800)
            with pytest.raises(PortConflictError):
                r.assign_port("/home/tom/project-b", preferred_port=19800, allow_fallback=False)

    def test_conflict_on_preferred_port_falls_back_when_allowed(self):
        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a", preferred_port=19800)
            a = r.assign_port("/home/tom/project-b", preferred_port=19800, allow_fallback=True)
        assert a.port != 19800
        assert a.assignment_type == "auto"

    def test_raises_port_exhausted_when_range_full(self):
        from iris_devtester.ports.exceptions import PortExhaustedError

        r = self._make_registry((19800, 19801))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a")
            r.assign_port("/home/tom/project-b")
            with pytest.raises(PortExhaustedError):
                r.assign_port("/home/tom/project-c")

    def test_reassigns_when_existing_port_no_longer_free(self):
        r = self._make_registry((19800, 19810))
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            a1 = r.assign_port("/home/tom/project-a")
        assert a1.port == 19800

        # Simulate port 19800 now occupied
        def port_occupied(port):
            return port != 19800

        with patch.object(r, "_is_host_port_free", side_effect=port_occupied), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            a2 = r.assign_port("/home/tom/project-a")
        assert a2.port != 19800

    def test_multiple_projects_get_different_ports(self):
        r = self._make_registry((19800, 19810))
        ports = []
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            for i in range(5):
                a = r.assign_port(f"/home/tom/project-{i}")
                ports.append(a.port)
        assert len(set(ports)) == 5


# ---------------------------------------------------------------------------
# PortRegistry release_port
# ---------------------------------------------------------------------------


class TestPortRegistryRelease:
    def _make_registry(self):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        return PortRegistry(registry_path=reg_path, port_range=(19800, 19810))

    def test_releases_existing_assignment(self):
        r = self._make_registry()
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a")
        r.release_port("/home/tom/project-a")
        assert r.get_assignment("/home/tom/project-a") is None

    def test_raises_key_error_when_not_found(self):
        r = self._make_registry()
        with pytest.raises(KeyError, match="No port assignment"):
            r.release_port("/nonexistent/project")


# ---------------------------------------------------------------------------
# PortRegistry list_all / get_assignment / clear_all
# ---------------------------------------------------------------------------


class TestPortRegistryListAndQuery:
    def _make_registry(self):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        return PortRegistry(registry_path=reg_path, port_range=(19800, 19810))

    def test_list_all_empty_on_new_registry(self):
        r = self._make_registry()
        assert r.list_all() == []

    def test_list_all_returns_all_assignments(self):
        r = self._make_registry()
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a")
            r.assign_port("/home/tom/project-b")
        all_assignments = r.list_all()
        assert len(all_assignments) == 2

    def test_get_assignment_returns_none_for_unknown(self):
        r = self._make_registry()
        assert r.get_assignment("/no/such/project") is None

    def test_get_assignment_returns_assignment(self):
        r = self._make_registry()
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            expected = r.assign_port("/home/tom/project-a")
        found = r.get_assignment("/home/tom/project-a")
        assert found is not None
        assert found.port == expected.port

    def test_clear_all_removes_all_assignments(self):
        r = self._make_registry()
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a")
            r.assign_port("/home/tom/project-b")
        r.clear_all()
        assert r.list_all() == []


# ---------------------------------------------------------------------------
# PortRegistry cleanup_stale
# ---------------------------------------------------------------------------


class TestPortRegistryCleanupStale:
    def _make_registry(self):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        return PortRegistry(registry_path=reg_path, port_range=(19800, 19810))

    def test_returns_empty_list_when_docker_not_importable(self):
        r = self._make_registry()
        with patch.dict("sys.modules", {"docker": None}):
            result = r.cleanup_stale()
        assert result == []

    def test_removes_stale_assignments(self):
        r = self._make_registry()
        # Manually seed a stale assignment (container_name set to something not running)
        data = {
            "schema_version": "1.0",
            "assignments": [
                {
                    "project_path": "/home/tom/stale-project",
                    "port": 19800,
                    "assigned_at": datetime.now().isoformat(),
                    "assignment_type": "auto",
                    "status": "active",
                    "container_name": "dead_container",
                }
            ],
        }
        r._write_registry(data)

        mock_container = MagicMock()
        mock_container.name = "live_container"
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        with patch("docker.from_env", return_value=mock_client):
            released = r.cleanup_stale()

        assert len(released) == 1
        assert released[0].project_path == "/home/tom/stale-project"
        assert released[0].status == "stale"
        # Stale entry removed from registry
        assert r.list_all() == []

    def test_keeps_active_assignments_without_container_name(self):
        r = self._make_registry()
        with patch.object(r, "_is_host_port_free", return_value=True), \
             patch.object(r, "_get_docker_bound_ports", return_value=set()):
            r.assign_port("/home/tom/project-a")  # container_name=None

        mock_client = MagicMock()
        mock_client.containers.list.return_value = []

        with patch("docker.from_env", return_value=mock_client):
            released = r.cleanup_stale()

        assert released == []
        assert len(r.list_all()) == 1

    def test_returns_empty_when_docker_daemon_unavailable(self):
        r = self._make_registry()
        mock_client = MagicMock()
        mock_client.containers.list.side_effect = Exception("Cannot connect")

        with patch("docker.from_env", return_value=mock_client):
            result = r.cleanup_stale()

        assert result == []


# ---------------------------------------------------------------------------
# _is_host_port_free
# ---------------------------------------------------------------------------


class TestIsHostPortFree:
    def _make_registry(self):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        return PortRegistry(registry_path=reg_path, port_range=(19800, 19810))

    def test_returns_false_when_ipv4_bind_raises_oserror(self):
        r = self._make_registry()

        mock_socket = MagicMock()
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        mock_socket.bind.side_effect = OSError(errno.EADDRINUSE, "Address in use")

        with patch("iris_devtester.ports.registry._socket.socket", return_value=mock_socket):
            result = r._is_host_port_free(19800)

        assert result is False

    def test_returns_true_when_both_binds_succeed(self):
        r = self._make_registry()

        mock_socket = MagicMock()
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        mock_socket.bind.return_value = None  # success

        with patch("iris_devtester.ports.registry._socket.socket", return_value=mock_socket):
            result = r._is_host_port_free(19800)

        assert result is True

    def test_returns_false_when_ipv6_bind_raises_eaddrinuse(self):
        r = self._make_registry()

        call_count = {"n": 0}

        def socket_factory(family, sock_type):
            call_count["n"] += 1
            m = MagicMock()
            m.__enter__ = MagicMock(return_value=m)
            m.__exit__ = MagicMock(return_value=False)
            if call_count["n"] == 1:
                # IPv4 succeeds
                m.bind.return_value = None
            else:
                # IPv6 fails with EADDRINUSE
                err = OSError(errno.EADDRINUSE, "Address in use")
                err.errno = errno.EADDRINUSE
                m.bind.side_effect = err
            return m

        with patch("iris_devtester.ports.registry._socket.socket", side_effect=socket_factory):
            result = r._is_host_port_free(19800)

        assert result is False


# ---------------------------------------------------------------------------
# _get_docker_bound_ports
# ---------------------------------------------------------------------------


class TestGetDockerBoundPorts:
    def _make_registry(self, port_range=(19800, 19810)):
        from iris_devtester.ports.registry import PortRegistry

        tmpdir = tempfile.mkdtemp()
        reg_path = Path(tmpdir) / "r.json"
        return PortRegistry(registry_path=reg_path, port_range=port_range)

    def test_returns_empty_set_when_docker_not_importable(self):
        r = self._make_registry()
        with patch.dict("sys.modules", {"docker": None}):
            result = r._get_docker_bound_ports()
        assert result == set()

    def test_returns_ports_from_docker_containers(self):
        r = self._make_registry(port_range=(19800, 19810))

        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {
                    "1972/tcp": [{"HostPort": "19805"}],
                }
            }
        }
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        with patch("docker.from_env", return_value=mock_client):
            result = r._get_docker_bound_ports()

        assert 19805 in result

    def test_ignores_ports_outside_range(self):
        r = self._make_registry(port_range=(19800, 19810))

        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {
                    "80/tcp": [{"HostPort": "8080"}],  # outside 19800-19810
                }
            }
        }
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        with patch("docker.from_env", return_value=mock_client):
            result = r._get_docker_bound_ports()

        assert result == set()

    def test_returns_empty_set_when_docker_raises(self):
        r = self._make_registry()
        with patch("docker.from_env", side_effect=Exception("daemon down")):
            result = r._get_docker_bound_ports()
        assert result == set()


# ---------------------------------------------------------------------------
# ports/__init__.py coverage
# ---------------------------------------------------------------------------


class TestPortsInit:
    def test_imports_from_ports_package(self):
        from iris_devtester.ports import PortRegistry
        from iris_devtester.ports.assignment import PortAssignment
        from iris_devtester.ports.exceptions import (
            PortAssignmentTimeoutError,
            PortConflictError,
            PortExhaustedError,
        )

        assert PortRegistry is not None
        assert PortAssignment is not None
        assert PortExhaustedError is not None
        assert PortConflictError is not None
        assert PortAssignmentTimeoutError is not None
