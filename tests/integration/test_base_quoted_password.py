"""Feature 036: values travel to IRIS through the exec environment, not the command.

T001 probe: confirms that a password containing shell and ObjectScript
metacharacters survives ``exec_run(environment=...)`` plus the IRIS
environment-variable lookup unchanged (the FR-017 assumption).
T009 phase gate: a user whose password contains a quote can connect.

Each test creates and removes its own uniquely named container. Tests skip
when Docker or the image is unavailable.
"""

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

NASTY_PASSWORD = "a\"b'c$(x)"

IMAGES = [
    pytest.param("intersystemsdc/iris-community:latest-em", id="community"),
    pytest.param("intersystemsdc/irishealth-community:latest", id="health"),
]

PROBE_SCRIPT = """iris session iris -U USER <<'IDT_EOF'
Set pw=$system.Util.GetEnviron("IDT_PW")
Set ^IDTProbe=pw
Write "IDT_VALUE[",^IDTProbe,"]",!
Halt
IDT_EOF
"""


def _docker_client():
    docker = pytest.importorskip("docker")
    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Docker not available: {exc}")
    return client


def _require_image(client, image):
    try:
        client.images.get(image)
    except Exception:
        pytest.skip(f"image {image} not present locally")


@pytest.mark.parametrize("image", IMAGES)
def test_environment_value_transfer_is_exact(image):
    """T001: the exec environment delivers the value byte for byte."""
    from iris_devtester.containers._base import IRISDockerContainer

    client = _docker_client()
    _require_image(client, image)

    name = f"idt036-probe-{uuid.uuid4().hex[:8]}"
    container = IRISDockerContainer(image=image).with_name(name)
    try:
        container.start()
        result = container._container.exec_run(
            ["sh", "-c", PROBE_SCRIPT], environment={"IDT_PW": NASTY_PASSWORD}
        )
        output = result.output.decode("utf-8", "replace")
        assert f"IDT_VALUE[{NASTY_PASSWORD}]" in output, output
    finally:
        container.stop(force=True, delete_volume=True)


def test_user_with_quoted_password_can_connect(monkeypatch):
    """T009 phase gate: create a user whose password holds quotes, then log in."""
    from iris_devtester.containers.iris_container import IRISContainer

    client = _docker_client()
    image = "intersystemsdc/iris-community:latest-em"
    _require_image(client, image)

    username = "idtquoteuser"
    monkeypatch.setenv("IRIS_USERNAME", username)
    monkeypatch.setenv("IRIS_PASSWORD", NASTY_PASSWORD)
    monkeypatch.delenv("IRIS_NAMESPACE", raising=False)

    name = f"idt036-quote-{uuid.uuid4().hex[:8]}"
    container = IRISContainer(image=image).with_name(name)
    try:
        container.start()
        # The base created the user through the exec environment; make the
        # account usable for DBAPI (CallIn on, no forced password change).
        container.enable_callin_service()
        result = container._container.exec_run(
            ["sh", "-c", _UNEXPIRE_SCRIPT], environment={"IDT_USERNAME": username}
        )
        assert b"IDT_OK" in result.output, result.output

        import iris

        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(1972))
        conn = iris.connect(host, port, "USER", username, NASTY_PASSWORD)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1
        finally:
            conn.close()
    finally:
        container.stop(force=True, delete_volume=True)


_UNEXPIRE_SCRIPT = """iris session iris -U %SYS <<'IDT_EOF'
Set u=$system.Util.GetEnviron("IDT_USERNAME")
Set p("ChangePassword")=0,p("PasswordNeverExpires")=1,p("Enabled")=1
Set sc=##class(Security.Users).Modify(u,.p)
Write $Select($system.Status.IsOK(sc):"IDT_OK",1:"IDT_ERR:"_$system.Status.GetErrorText(sc)),!
Halt
IDT_EOF
"""
