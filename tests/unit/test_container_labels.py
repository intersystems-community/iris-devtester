"""Feature 036 US4: containers created by ``container up`` carry idt labels."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.containers import labels as label_mod
from iris_devtester.utils.iris_container_adapter import IRISContainerManager


def _fake_docker():
    client = MagicMock()
    created = MagicMock()
    client.containers.create.return_value = created
    return client


def _create(image="intersystemsdc/iris-community:latest-em"):
    config = ContainerConfig(container_name="idt036-labels", image=image)
    client = _fake_docker()
    with patch("iris_devtester.utils.iris_container_adapter.docker.from_env", return_value=client):
        IRISContainerManager._create_with_docker_sdk(config)
    return client.containers.create.call_args.kwargs


# Captured from the implementation before labels were added (T026).
UP_OUTPUT_SNAPSHOT = [
    "⚡ Creating container from zero-config defaults",
    "  → Container name: idt036-cli",
    "  → Image: img:cli (custom)",
    "  → Edition: community",
    "  → Image: img:cli",
    "  → Ports: 1972, 52773",
    "⏳ Creating container with Docker SDK...",
    "✓ Container 'idt036-cli' created and started",
    "⏳ Verifying container persistence...",
    "✓ Container persistence verified",
    "⏳ Waiting for container to be healthy...",
    "⏳ Enabling CallIn service...",
    "✓ CallIn service enabled",
    "✓ Container 'idt036-cli' is running and healthy",
    "Connection Information:",
    "  SuperServer: localhost:1972",
    "  Web Portal:  http://localhost:52773",
    "  Namespace:   USER",
    "  Username:    _SYSTEM",
    "  Password:    SYS",
]


class TestLabelConstants:
    def test_keys_match_contract(self):
        assert label_mod.LABEL_CREATED_BY == "io.iris-devtester.created-by"
        assert label_mod.LABEL_CREATED_BY_VALUE == "idt"
        assert label_mod.LABEL_IMAGE == "io.iris-devtester.image"

    def test_build_labels_with_image(self):
        assert label_mod.build_labels("img:1") == {
            "io.iris-devtester.created-by": "idt",
            "io.iris-devtester.image": "img:1",
        }

    @pytest.mark.parametrize("ref", ["", None])
    def test_image_label_omitted_when_unknown(self, ref):
        assert label_mod.build_labels(ref) == {"io.iris-devtester.created-by": "idt"}


class TestSdkPathLabels:
    def test_create_passes_both_labels(self):
        kwargs = _create(image="my.registry/iris:1")
        assert kwargs["labels"] == {
            "io.iris-devtester.created-by": "idt",
            "io.iris-devtester.image": "my.registry/iris:1",
        }

    def test_existing_config_source_key_untouched(self):
        # The adapter must not add, remove or rename the unrelated config.source key.
        kwargs = _create()
        assert "iris-devtester.config.source" not in kwargs["labels"]

    def test_other_create_arguments_unchanged(self):
        kwargs = _create()
        assert kwargs["name"] == "idt036-labels"
        assert kwargs["detach"] is True
        assert set(kwargs["ports"]) == {"1972/tcp", "52773/tcp"}


class TestContainerUpCli:
    def _run(self):
        from iris_devtester.cli.container import container_group

        client = _fake_docker()
        runner = CliRunner()
        ok = SimpleNamespace(success=True)
        with (
            runner.isolated_filesystem(),
            patch(
                "iris_devtester.utils.iris_container_adapter.docker.from_env", return_value=client
            ),
            patch(
                "iris_devtester.cli.container.IRISContainerManager.get_existing", return_value=None
            ),
            patch("iris_devtester.cli.container.verify_container_persistence", return_value=ok),
            patch("iris_devtester.cli.container.health_checks.wait_for_healthy"),
            patch("iris_devtester.cli.container.health_checks.enable_callin_service"),
            patch(
                "iris_devtester.cli.container._resolve_port_mappings", return_value=(1972, 52773)
            ),
        ):
            result = runner.invoke(
                container_group, ["up", "--name", "idt036-cli", "--image", "img:cli"]
            )
        return result, client

    def test_up_creates_container_with_labels(self):
        result, client = self._run()
        assert result.exit_code == 0, result.output
        labels = client.containers.create.call_args.kwargs["labels"]
        assert labels["io.iris-devtester.created-by"] == "idt"
        assert labels["io.iris-devtester.image"] == "img:cli"

    def test_up_output_unchanged(self):
        result, _ = self._run()
        assert result.exit_code == 0, result.output
        assert "label" not in result.output.lower()
        assert [line for line in result.output.splitlines() if line.strip()] == UP_OUTPUT_SNAPSHOT
