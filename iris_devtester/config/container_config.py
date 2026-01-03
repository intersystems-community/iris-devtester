"""Container configuration model for IRIS lifecycle management."""

import os
import re
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from iris_devtester.config.yaml_loader import load_yaml


class ContainerConfig(BaseModel):
    """
    Container configuration model.

    Represents user-defined configuration for IRIS container lifecycle operations.
    Can be loaded from YAML file, environment variables, or use zero-config defaults.

    Attributes:
        edition: IRIS edition ('community' or 'enterprise')
        container_name: Docker container name
        superserver_port: SuperServer port mapping (1024-65535)
        webserver_port: Management Portal port mapping (1024-65535)
        namespace: Default IRIS namespace
        password: _SYSTEM user password
        license_key: License key for Enterprise edition (required if edition='enterprise')
        volumes: List of volume mount strings (e.g., './data:/external')
        image_tag: Docker image tag to use

    Example:
        >>> # Zero-config defaults
        >>> config = ContainerConfig.default()

        >>> # From YAML file
        >>> config = ContainerConfig.from_yaml("iris-config.yml")

        >>> # From environment variables
        >>> config = ContainerConfig.from_env()

        >>> # Explicit construction
        >>> config = ContainerConfig(
        ...     edition="community",
        ...     container_name="my_iris",
        ...     superserver_port=1972,
        ...     webserver_port=52773,
        ...     namespace="USER",
        ...     password="SYS",
        ...     volumes=[],
        ...     image_tag="latest"
        ... )
    """

    edition: Literal["community", "enterprise"] = Field(
        default="community",
        description="IRIS edition to use"
    )
    container_name: str = Field(
        default="iris_db",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
        description="Container name identifier"
    )
    superserver_port: int = Field(
        default=1972,
        ge=1024,
        le=65535,
        description="SuperServer port mapping"
    )
    webserver_port: int = Field(
        default=52773,
        ge=1024,
        le=65535,
        description="Management Portal port mapping"
    )
    namespace: str = Field(
        default="USER",
        pattern=r"^[A-Z][A-Z0-9%]*$",
        description="Default IRIS namespace"
    )
    password: str = Field(
        default="SYS",
        min_length=1,
        description="_SYSTEM user password"
    )
    license_key: Optional[str] = Field(
        default=None,
        description="License key for Enterprise edition"
    )
    volumes: List[str] = Field(
        default_factory=list,
        description="Volume mount strings"
    )
    image: Optional[str] = Field(
        default=None,
        description="Full Docker image name (overrides edition/image_tag)"
    )
    image_tag: str = Field(
        default="latest",
        description="Docker image tag"
    )

    @field_validator("container_name")
    @classmethod
    def validate_container_name(cls, v: str) -> str:
        """Validate Docker container name format."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError(
                f"Invalid container_name: {v}\n"
                "Container names must start with alphanumeric and contain only [a-zA-Z0-9_.-]"
            )
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate IRIS namespace format."""
        if not re.match(r"^[A-Z][A-Z0-9%]*$", v):
            raise ValueError(
                f"Invalid namespace: {v}\n"
                "Namespaces must start with uppercase letter and contain only [A-Z0-9%]"
            )
        return v

    @model_validator(mode="after")
    def validate_enterprise_license(self) -> "ContainerConfig":
        """Ensure license_key is provided for enterprise edition."""
        if self.edition == "enterprise" and not self.license_key:
            raise ValueError(
                "license_key is required for enterprise edition\n"
                "\n"
                "How to fix it:\n"
                "  1. Add license_key to iris-config.yml:\n"
                "     license_key: 'YOUR-LICENSE-KEY'\n"
                "  2. Or set environment variable:\n"
                "     export IRIS_LICENSE_KEY='YOUR-LICENSE-KEY'\n"
                "\n"
                "Documentation:\n"
                "  https://iris-devtester.readthedocs.io/config/enterprise/"
            )
        return self

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> "ContainerConfig":
        """
        Load configuration from YAML file.

        Args:
            file_path: Path to iris-config.yml file

        Returns:
            ContainerConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML structure is invalid

        Example:
            >>> config = ContainerConfig.from_yaml("iris-config.yml")
        """
        file_path = Path(file_path)
        yaml_data = load_yaml(file_path)

        # Transform YAML structure to flat model
        # YAML has nested ports: {superserver: 1972, webserver: 52773}
        # Model expects flat: superserver_port, webserver_port
        config_data = {}

        # Map direct fields
        for field in ["edition", "container_name", "namespace", "password", "license_key", "volumes", "image", "image_tag"]:
            if field in yaml_data:
                config_data[field] = yaml_data[field]

        # Map nested ports
        if "ports" in yaml_data:
            ports = yaml_data["ports"]
            if "superserver" in ports:
                config_data["superserver_port"] = ports["superserver"]
            if "webserver" in ports:
                config_data["webserver_port"] = ports["webserver"]

        return cls(**config_data)

    @classmethod
    def from_env(cls) -> "ContainerConfig":
        """
        Load configuration from environment variables.

        Environment variables:
            IRIS_EDITION: 'community' or 'enterprise'
            IRIS_CONTAINER_NAME: Container name
            IRIS_SUPERSERVER_PORT: SuperServer port (default: 1972)
            IRIS_WEBSERVER_PORT: Web portal port (default: 52773)
            IRIS_NAMESPACE: Default namespace (default: USER)
            IRIS_PASSWORD: _SYSTEM password (default: SYS)
            IRIS_LICENSE_KEY: License key (required for enterprise)
            IRIS_VOLUMES: Comma-separated volume mounts
            IRIS_IMAGE_TAG: Image tag (default: latest)

        Returns:
            ContainerConfig instance

        Example:
            >>> os.environ["IRIS_EDITION"] = "enterprise"
            >>> os.environ["IRIS_LICENSE_KEY"] = "ABC-123"
            >>> config = ContainerConfig.from_env()
        """
        config_data = {}

        # Map environment variables to fields
        env_mappings = {
            "IRIS_EDITION": "edition",
            "IRIS_CONTAINER_NAME": "container_name",
            "IRIS_SUPERSERVER_PORT": ("superserver_port", int),
            "IRIS_WEBSERVER_PORT": ("webserver_port", int),
            "IRIS_NAMESPACE": "namespace",
            "IRIS_PASSWORD": "password",
            "IRIS_LICENSE_KEY": "license_key",
            "IRIS_IMAGE": "image",
            "IRIS_IMAGE_TAG": "image_tag",
        }

        for env_var, field_info in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                if isinstance(field_info, tuple):
                    field_name, converter = field_info
                    config_data[field_name] = converter(value)
                else:
                    config_data[field_info] = value

        # Handle volumes (comma-separated)
        if "IRIS_VOLUMES" in os.environ:
            volumes_str = os.environ["IRIS_VOLUMES"]
            config_data["volumes"] = [v.strip() for v in volumes_str.split(",") if v.strip()]

        return cls(**config_data)

    @classmethod
    def default(cls) -> "ContainerConfig":
        """
        Create configuration with zero-config defaults.

        Returns:
            ContainerConfig instance with all default values

        Example:
            >>> config = ContainerConfig.default()
            >>> assert config.edition == "community"
            >>> assert config.container_name == "iris_db"
            >>> assert config.superserver_port == 1972
        """
        return cls()

    def get_image_name(self) -> str:
        if self.image:
            return self.image

        if self.edition == "community":

            # Bug Fix #1: Community images use 'intersystemsdc/' prefix on Docker Hub
            return f"intersystemsdc/iris-community:{self.image_tag}"
        else:
            return f"intersystems/iris:{self.image_tag}"

    def validate_volume_paths(self) -> List[str]:
        """
        Validate that all volume host paths exist (Feature 011 - T011).

        Returns:
            List of error messages (empty if all paths valid)

        Example:
            >>> config = ContainerConfig(volumes=["./data:/external", "/tmp:/temp"])
            >>> errors = config.validate_volume_paths()
            >>> if errors:
            ...     for error in errors:
            ...         print(error)
        """
        errors = []
        for volume in self.volumes:
            parts = volume.split(":")
            if len(parts) < 2:
                errors.append(
                    f"Volume has invalid format: {volume}\n"
                    f"  Expected format: host:container or host:container:mode\n"
                    f"  Fix the volume specification in configuration"
                )
                continue

            host_path = parts[0]
            if not os.path.exists(host_path):
                errors.append(
                    f"Volume host path does not exist: {host_path}\n"
                    f"  Required by volume mount: {volume}\n"
                    f"  Create the directory or fix the path in configuration"
                )

        return errors

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "edition": "community",
                "container_name": "iris_db",
                "superserver_port": 1972,
                "webserver_port": 52773,
                "namespace": "USER",
                "password": "SYS",
                "license_key": None,
                "volumes": ["./data:/external"],
                "image_tag": "latest"
            }
        }
