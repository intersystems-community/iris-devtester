"""
Integration tests for IRISContainer.attach() method.

Tests verify attaching to external IRIS containers (docker-compose workflows).
"""

import pytest
from iris_devtester.containers.iris_container import IRISContainer


class TestIRISContainerAttachIntegration:
    """Integration tests for IRISContainer.attach() with real containers."""

    def test_attach_to_testcontainer(self, iris_container):
        """
        Test attaching to existing testcontainer instance.

        Expected: Successfully attaches, can use utility methods.
        """
        container_name = iris_container.get_container_name()

        # Attach to existing container
        attached_iris = IRISContainer.attach(container_name)

        assert attached_iris is not None
        assert attached_iris._is_attached is True
        assert attached_iris._container_name == container_name

    def test_attached_container_get_connection(self, iris_container):
        """
        Test that attached container can get database connection.

        Expected: get_connection() works on attached instance.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        # Attach and get connection
        attached_iris = IRISContainer.attach(container_name)
        conn = attached_iris.get_connection()

        assert conn is not None

        # Verify connection works
        cursor = conn.cursor()
        cursor.execute("SELECT $HOROLOG")
        result = cursor.fetchone()
        assert result is not None

    def test_attached_container_enable_callin(self, iris_container):
        """
        Test that attached container can enable CallIn service.

        Expected: enable_callin_service() works on attached instance.
        """
        container_name = iris_container.get_container_name()

        # Attach and enable CallIn
        attached_iris = IRISContainer.attach(container_name)
        success = attached_iris.enable_callin_service()

        assert success is True

    def test_attached_container_reset_password(self, iris_container):
        """
        Test that attached container can reset password.

        Expected: reset_password() works on attached instance.
        """
        container_name = iris_container.get_container_name()

        # Attach and reset password
        attached_iris = IRISContainer.attach(container_name)
        success = attached_iris.reset_password(username="_SYSTEM", new_password="SYS")

        assert success is True

    def test_attached_container_get_config(self, iris_container):
        """
        Test that attached container returns valid config.

        Expected: get_config() returns IRISConfig with discovered port.
        """
        container_name = iris_container.get_container_name()

        # Attach and get config
        attached_iris = IRISContainer.attach(container_name)
        config = attached_iris.get_config()

        assert config is not None
        assert config.host == "localhost"
        assert config.port > 0  # Should have discovered port
        assert config.namespace == "USER"

    def test_attach_to_nonexistent_container_raises_error(self):
        """
        Test that attaching to non-existent container raises ValueError.

        Expected: ValueError with remediation steps.
        """
        with pytest.raises(ValueError) as exc_info:
            IRISContainer.attach("nonexistent_container_xyz")

        error_message = str(exc_info.value)
        assert "not found or not running" in error_message
        assert "docker ps" in error_message
        assert "How to fix it:" in error_message

    def test_attach_discovers_port_mapping(self, iris_container):
        """
        Test that attach() auto-discovers container port mapping.

        Expected: Correctly identifies exposed port for IRIS.
        """
        container_name = iris_container.get_container_name()

        # Attach and check port discovery
        attached_iris = IRISContainer.attach(container_name)
        config = attached_iris.get_config()

        # Port should be discovered (either 1972 or random mapped port)
        assert config.port in range(1024, 65536), f"Port {config.port} should be valid"

    def test_attached_container_lifecycle_guards(self, iris_container):
        """
        Test that attached container prevents lifecycle operations.

        Expected: Context manager usage should fail (planned for future).
        Note: This test documents expected behavior - guards not yet implemented.
        """
        container_name = iris_container.get_container_name()

        # Attach to existing container
        attached_iris = IRISContainer.attach(container_name)

        # For now, just verify it's marked as attached
        # (Lifecycle guards will be added in future iteration if needed)
        assert attached_iris._is_attached is True
