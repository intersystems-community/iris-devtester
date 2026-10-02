"""Share the ``idt image`` fixtures (defined in tests/unit/image/conftest.py) with e2e tests."""

from tests.unit.image.conftest import (  # noqa: F401
    elf_amd64,
    elf_arm64,
    fake_docker,
    fake_health,
    fake_password,
    fake_runner,
    image_archive,
    installer_kit,
)
