"""Management of temporary CPF merge files for IRIS containers."""

import os
import tempfile
import weakref
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

class TempCPFManager:
    """
    Handles the lifecycle of temporary CPF files.
    
    Ensures files are created securely and cleaned up after container shutdown.
    Uses weakref.finalize for crash-resistant cleanup.
    """
    
    def __init__(self):
        self._temp_files: Set[str] = set()
    
    def create_temp_cpf(self, content: str) -> str:
        """
        Create a temporary CPF file with the provided content.
        
        Args:
            content: Raw CPF string content.
            
        Returns:
            Absolute path to the created temporary file.
        """
        # Create file but don't delete on close (we need Docker to read it)
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.cpf', delete=False)
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            
            file_path = os.path.abspath(tmp.name)
            self._temp_files.add(file_path)
            
            # Register for automatic cleanup
            weakref.finalize(self, self._delete_file, file_path)
            
            logger.debug(f"Created temporary CPF file: {file_path}")
            return file_path
        finally:
            tmp.close()
            
    def _delete_file(self, file_path: str):
        """Internal helper to safely delete a file."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Deleted temporary CPF file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary CPF file {file_path}: {e}")
            
    def cleanup(self):
        """Manual cleanup of all tracked temporary files."""
        for file_path in list(self._temp_files):
            self._delete_file(file_path)
            self._temp_files.discard(file_path)
