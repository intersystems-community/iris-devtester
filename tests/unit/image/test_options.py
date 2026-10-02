import dataclasses

import pytest

from iris_devtester.cli.image import options
from iris_devtester.cli.image.options import StartOptions


def test_constants():
    assert options.BUILD_TIMEOUT == 900
    assert options.LOAD_TIMEOUT == 300
    assert options.HEALTH_TIMEOUT == 120
    assert options.RUN_TIMEOUT == 60
    assert options.KILL_GRACE == 3


def test_label_keys_exact():
    assert options.LABEL_CREATED_BY == "io.iris-devtester.created-by"
    assert options.LABEL_IMAGE == "io.iris-devtester.image"
    assert options.LABEL_CREATED_BY_VALUE == "idt"


def test_build_labels():
    assert options.build_labels("img:1") == {
        "io.iris-devtester.created-by": "idt",
        "io.iris-devtester.image": "img:1",
    }


def test_start_options_is_frozen():
    opts = StartOptions(name="n", superserver_port=1972, web_port=None, password="SYS")
    with pytest.raises(dataclasses.FrozenInstanceError):
        opts.name = "other"  # type: ignore[misc]


def test_start_options_defaults():
    opts = StartOptions(name="n", superserver_port=1972, web_port=52773, password="SYS")
    assert opts.show_password is False
    assert opts.no_unexpire is False
    assert opts.health_timeout == options.HEALTH_TIMEOUT
    assert opts.run_timeout == options.RUN_TIMEOUT
    assert opts.license_mount is None
    assert opts.replace is False
    assert opts.cap_ipc_lock is False
    assert opts.labels == {}
