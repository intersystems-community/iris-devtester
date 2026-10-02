"""Compatibility shim: the image commands now live in ``iris_devtester.cli.image``."""

from iris_devtester.cli.image import image_group

__all__ = ["image_group"]
