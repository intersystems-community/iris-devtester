import pytest

from iris_devtester.cli.image.collision import resolve_name_collision
from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.options import LABEL_CREATED_BY, build_labels

LABELLED = build_labels("iris-test:1")

REUSABLE = ["created", "dead"]
LIVE = ["running", "exited", "paused", "restarting"]

REASONS = {
    "running": "it is running",
    "restarting": "it is running",
    "paused": "it is running",
    "exited": "it holds data",
}


def _resolve(fake_docker, replace):
    lines = []
    resolve_name_collision(fake_docker, "box", replace, echo=lines.append)
    return lines


def test_no_container_proceeds(fake_docker):
    assert _resolve(fake_docker, False) == []
    assert _resolve(fake_docker, True) == []


@pytest.mark.parametrize("replace", [False, True])
@pytest.mark.parametrize("status", REUSABLE)
def test_labelled_created_or_dead_removed_with_one_line(fake_docker, status, replace):
    c = fake_docker.add("box", status, LABELLED)
    lines = _resolve(fake_docker, replace)
    assert len(lines) == 1
    assert "box" in lines[0]
    assert c.removed == [{"force": True, "v": False}]


@pytest.mark.parametrize("status", LIVE)
def test_labelled_live_refused_without_replace(fake_docker, status):
    c = fake_docker.add("box", status, LABELLED)
    with pytest.raises(ImageCommandError) as ei:
        _resolve(fake_docker, False)
    err = ei.value
    assert err.exit_code == 2
    assert REASONS[status] in err.what
    assert "--replace" in err.fix
    assert c.removed == []
    assert err.why and err.fix


@pytest.mark.parametrize("status", LIVE)
def test_labelled_live_removed_with_replace(fake_docker, status):
    c = fake_docker.add("box", status, LABELLED, image="iris-test:1")
    lines = _resolve(fake_docker, True)
    assert len(lines) == 1
    assert "box" in lines[0] and status in lines[0] and "iris-test:1" in lines[0]
    assert c.removed == [{"force": True, "v": False}]  # container only, volumes kept


@pytest.mark.parametrize("replace", [False, True])
@pytest.mark.parametrize("status", REUSABLE + LIVE)
def test_unlabelled_always_refused(fake_docker, status, replace):
    c = fake_docker.add("box", status, {})
    with pytest.raises(ImageCommandError) as ei:
        _resolve(fake_docker, replace)
    err = ei.value
    assert err.exit_code == 2
    assert "it was not created by idt" in err.what
    assert "--replace" not in err.fix
    assert "docker rm" in err.fix
    assert c.removed == []


def test_label_with_wrong_value_is_unlabelled(fake_docker):
    fake_docker.add("box", "exited", {LABEL_CREATED_BY: "someone-else"})
    with pytest.raises(ImageCommandError) as ei:
        _resolve(fake_docker, True)
    assert "it was not created by idt" in ei.value.what


def test_refusal_is_three_part(fake_docker):
    from iris_devtester.cli.image.errors import render_error

    fake_docker.add("box", "running", LABELLED)
    with pytest.raises(ImageCommandError) as ei:
        _resolve(fake_docker, False)
    text = render_error(ei.value)
    for part in ("What went wrong:", "Why it matters:", "How to fix it:"):
        assert part in text


def test_image_unknown_still_announces(fake_docker):
    c = fake_docker.add("box", "exited", LABELLED, image=None)
    lines = _resolve(fake_docker, True)
    assert len(lines) == 1
    assert c.removed
