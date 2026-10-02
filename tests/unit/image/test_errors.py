import pytest

from iris_devtester.cli.image.errors import (
    EXIT_BAD_INPUT,
    EXIT_FAILURE,
    EXIT_TIMEOUT,
    ImageCommandError,
    render_error,
)


def test_holds_fields():
    err = ImageCommandError("w", "y", "f", exit_code=2)
    assert (err.what, err.why, err.fix, err.exit_code) == ("w", "y", "f", 2)


def test_default_exit_code_is_failure():
    assert ImageCommandError("w", "y", "f").exit_code == EXIT_FAILURE == 1


def test_exit_code_constants():
    assert (EXIT_FAILURE, EXIT_BAD_INPUT, EXIT_TIMEOUT) == (1, 2, 5)


@pytest.mark.parametrize("code", [0, 3, 4, 130])
def test_rejects_other_exit_codes(code):
    with pytest.raises(ValueError):
        ImageCommandError("w", "y", "f", exit_code=code)


@pytest.mark.parametrize("fix", ["", "   "])
def test_rejects_empty_fix(fix):
    with pytest.raises(ValueError):
        ImageCommandError("w", "y", fix)


def test_render_has_three_parts():
    text = render_error(ImageCommandError("it broke", "data lost", "run idt again", title="Oops"))
    assert text.splitlines()[0] == "Oops"
    assert "What went wrong:\n  it broke" in text
    assert "Why it matters:\n  data lost" in text
    assert "How to fix it:\n  run idt again" in text


def test_render_never_includes_password():
    err = ImageCommandError("failed with s3cret", "pw s3cret", "use --password s3cret")
    text = render_error(err, secrets=["s3cret"])
    assert "s3cret" not in text
    assert "********" in text


def test_render_ignores_empty_secret():
    text = render_error(ImageCommandError("w", "y", "f"), secrets=["", None])
    assert "What went wrong" in text
