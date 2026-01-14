import os
import pytest
from iris_devtester.containers.cpf_manager import TempCPFManager

@pytest.mark.unit
def test_temp_cpf_creation():
    manager = TempCPFManager()
    content = "[config]\nglobals=0,0,128,0,0,0"
    
    file_path = manager.create_temp_cpf(content)
    
    try:
        assert os.path.exists(file_path)
        assert file_path.endswith('.cpf')
        
        with open(file_path, 'r') as f:
            assert f.read() == content
    finally:
        manager.cleanup()
        assert not os.path.exists(file_path)

@pytest.mark.unit
def test_temp_cpf_cleanup_on_garbage_collection():
    manager = TempCPFManager()
    content = "test content"
    file_path = manager.create_temp_cpf(content)
    
    assert os.path.exists(file_path)
    
    del manager
    import gc
    gc.collect()
    
    if os.path.exists(file_path):
        os.unlink(file_path)
