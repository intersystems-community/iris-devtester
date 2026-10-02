"""print_connection_info password masking (feature 035).

Kept separate from test_progress.py so that file stays untouched.
"""

from iris_devtester.utils.progress import print_connection_info


def test_default_prints_real_password(capsys):
    print_connection_info("c", 1972, 52773, "USER", password="hunter2")
    out = capsys.readouterr().out
    assert "Password:    hunter2" in out


def test_show_password_false_masks(capsys):
    print_connection_info("c", 1972, 52773, "USER", password="hunter2", show_password=False)
    out = capsys.readouterr().out
    assert "hunter2" not in out
    assert "********" in out
    assert "(set with --password)" in out
