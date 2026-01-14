import pytest
from iris_devtester import IRISContainer, get_connection

@pytest.mark.integration
def test_cpf_merge_with_prehashed_password():
    """Verify that providing a PasswordHash and clearing flags skips the password change requirement."""
    password_hash = "FBFE8593AEFA510C27FD184738D6E865A441DE98,u4ocm4qh"
    
    cpf_content = f"""
[Actions]
ModifyUser:Name=SuperUser,PasswordHash={password_hash},ChangePassword=0,PasswordNeverExpires=1
"""
    
    with IRISContainer.community().with_cpf_merge(cpf_content) as iris:
        config = iris.get_config()
        
        conn = get_connection(config, auto_retry=False)
        assert conn is not None
        conn.close()
