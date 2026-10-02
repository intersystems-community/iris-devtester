"""Image management CLI commands -- load or build kits-web tarballs into containers."""

import click


@click.group(name="image")
def image_group():
    """
    Docker image management commands.

    \b
    Load or build kits-web IRIS tarballs into Docker images and containers.

    \b
    QUICK START:
      # Docker-save tarball (has manifest.json inside):
      idt image load IRIS-2026.2.0AI.127.0-docker.tar.gz

      # ISC installer kit (has irisinstall inside -- most singlefile_kits):
      idt image build IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz \\
          --tag irishealth-ai:140 --name hs-iris --port 31974
    """


from iris_devtester.cli.image import build as _build_module  # noqa: E402,F401
from iris_devtester.cli.image import load as _load_module  # noqa: E402,F401

__all__ = ["image_group"]
