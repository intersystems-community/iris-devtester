import pytest
from iris_devtester import IRISContainer
from iris_devtester.config import CPFPreset

@pytest.mark.integration
def test_ci_optimized_preset_applies_memory_limits():
    """Verify that CI_OPTIMIZED preset reduces global buffers."""
    config = CPFPreset.CI_OPTIMIZED
    
    with IRISContainer.community().with_cpf_merge(config) as iris:
        iris.get_connection()
        
        check_script = 'Set obj = ##class(Config.config).Open() Write "VAL=",obj.globals'
        result = iris.execute_objectscript(check_script, namespace="%SYS")
        
        assert "VAL=0,0,256,0,0,0" in result
