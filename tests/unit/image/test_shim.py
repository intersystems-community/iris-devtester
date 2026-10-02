"""The old import path keeps working after the move into a package."""

from click.testing import CliRunner


def test_shim_exports_image_group():
    from iris_devtester.cli.image_commands import image_group

    assert image_group.name == "image"


def test_cli_package_exposes_same_object():
    import iris_devtester.cli as cli
    from iris_devtester.cli.image_commands import image_group

    assert cli.image is image_group


def test_help_lists_load_and_build():
    from iris_devtester.cli.image_commands import image_group

    result = CliRunner().invoke(image_group, ["--help"])
    assert result.exit_code == 0
    assert "load" in result.output
    assert "build" in result.output
