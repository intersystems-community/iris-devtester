import pytest
import subprocess
from iris_devtester.utils.password_reset import reset_password

@pytest.mark.integration
def test_password_reset_clears_flag_reliably(iris_container):
    container_name = iris_container.get_wrapped_container().name
    config = iris_container.get_config()
    
    success, msg = reset_password(
        container_name=container_name,
        username=config.username,
        new_password=config.password,
        hostname=config.host,
        port=config.port
    )
    
    assert success is True, f"Password reset failed: {msg}"
    
    verify_script = f'Set u="{config.username}"\\nIf ##class(Security.Users).Exists(u,.user,.sc) {{ Write "ChangePassword=",user.ChangePassword }} Else {{ Write "UserNotFound" }}\\nHalt'
    
    cmd = [
        "docker", "exec", "-i", container_name,
        "bash", "-c",
        f"echo -e '{verify_script}' | iris session IRIS -U %SYS"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert "ChangePassword=0" in result.stdout, f"ChangePassword flag still set! stdout: {result.stdout}"
