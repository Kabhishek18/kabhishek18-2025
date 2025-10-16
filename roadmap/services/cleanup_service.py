"""
Cleanup service for managing temporary files in the resume parser.
Ensures files are properly deleted after processing and handles orphaned files.
"""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional, List
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Service for managing temporary file cleanup in the resume parser.
    Provides immediate cleanup, error-safe cleanup, and timeout-based cleanup for orphaned files.
    """
    
    def __init__(self):
        self.temp_dir = getattr(settings, 'RESUME_PARSER_TEMP_DIR', tempfile.gettempdir())
        self.cleanup_timeout = getattr(settings, 'RESUME_PARSER_CLEANUP_TIMEOUT', 300)  # 5 minutes
        
    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Immediately delete a temporary file after processing.
        
        Args:
            file_path: Path to the temporary file to delete
            
        Returns:
            bool: True if file was successfully deleted, False otherwise
        """
        if not file_path:
            logger.warning("CleanupService: No file path provided for cleanup")
            return False
            
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"CleanupService: Successfully deleted temporary file: {file_path}")
                return True
            else:
                logger.debug(f"CleanupService: File already deleted or doesn't exist: {file_path}")
                return True
                
        except OSError as e:
            logger.error(f"CleanupService: Failed to delete temporary file {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"CleanupService: Unexpected error deleting file {file_path}: {e}")
            return False
    
    def cleanup_on_error(self, file_path: str) -> None:
        """
        Error-safe cleanup that works even when processing fails.
        This method never raises exceptions to avoid masking original errors.
        
        Args:
            file_path: Path to the temporary file to delete
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"CleanupService: Error cleanup - deleted file: {file_path}")
        except Exception as e:
            # Never raise exceptions in error cleanup to avoid masking original errors
            logger.error(f"CleanupService: Error cleanup failed for {file_path}: {e}")
    
    def cleanup_orphaned_files(self, max_age_minutes: Optional[int] = None) -> int:
        """
        Clean up orphaned temporary files that exceed the timeout threshold.
        
        Args:
            max_age_minutes: Maximum age in minutes for files to be kept (defaults to cleanup_timeout)
            
        Returns:
            int: Number of files cleaned up
        """
        if max_age_minutes is None:
            max_age_minutes = self.cleanup_timeout // 60
            
        cleanup_count = 0
        cutoff_time = time.time() - (max_age_minutes * 60)
        
        try:
            temp_path = Path(self.temp_dir)
            if not temp_path.exists():
                logger.debug(f"CleanupService: Temp directory doesn't exist: {self.temp_dir}")
                return 0
                
            # Look for resume-related temporary files
            patterns = ['resume_*', 'tmp_resume_*', '*.pdf.tmp']
            
            for pattern in patterns:
                for file_path in temp_path.glob(pattern):
                    try:
                        if file_path.is_file():
                            file_mtime = file_path.stat().st_mtime
                            if file_mtime < cutoff_time:
                                file_path.unlink()
                                cleanup_count += 1
                                logger.info(f"CleanupService: Cleaned up orphaned file: {file_path}")
                    except Exception as e:
                        logger.error(f"CleanupService: Failed to cleanup orphaned file {file_path}: {e}")
                        
        except Exception as e:
            logger.error(f"CleanupService: Error during orphaned file cleanup: {e}")
            
        logger.info(f"CleanupService: Cleaned up {cleanup_count} orphaned files")
        return cleanup_count
    
    def get_temp_file_path(self, prefix: str = "resume_", suffix: str = ".pdf") -> str:
        """
        Generate a secure temporary file path for resume processing.
        
        Args:
            prefix: Prefix for the temporary file name
            suffix: Suffix/extension for the temporary file
            
        Returns:
            str: Path to the temporary file
        """
        try:
            # Create a secure temporary file
            fd, temp_path = tempfile.mkstemp(
                prefix=prefix,
                suffix=suffix,
                dir=self.temp_dir
            )
            # Close the file descriptor as we only need the path
            os.close(fd)
            
            logger.debug(f"CleanupService: Generated temp file path: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"CleanupService: Failed to generate temp file path: {e}")
            raise
    
    def cleanup_multiple_files(self, file_paths: List[str]) -> int:
        """
        Clean up multiple temporary files at once.
        
        Args:
            file_paths: List of file paths to delete
            
        Returns:
            int: Number of files successfully deleted
        """
        success_count = 0
        
        for file_path in file_paths:
            if self.cleanup_temp_file(file_path):
                success_count += 1
                
        logger.info(f"CleanupService: Successfully cleaned up {success_count}/{len(file_paths)} files")
        return success_count
    
    def get_temp_dir_stats(self) -> dict:
        """
        Get statistics about the temporary directory.
        
        Returns:
            dict: Statistics including file count, total size, oldest file age
        """
        stats = {
            'file_count': 0,
            'total_size_bytes': 0,
            'oldest_file_age_minutes': 0,
            'temp_dir': self.temp_dir
        }
        
        try:
            temp_path = Path(self.temp_dir)
            if not temp_path.exists():
                return stats
                
            current_time = time.time()
            oldest_time = current_time
            
            for file_path in temp_path.iterdir():
                if file_path.is_file() and any(pattern in file_path.name for pattern in ['resume_', 'tmp_resume_', '.pdf.tmp']):
                    stats['file_count'] += 1
                    stats['total_size_bytes'] += file_path.stat().st_size
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < oldest_time:
                        oldest_time = file_mtime
            
            if oldest_time < current_time:
                stats['oldest_file_age_minutes'] = int((current_time - oldest_time) / 60)
                
        except Exception as e:
            logger.error(f"CleanupService: Error getting temp dir stats: {e}")
            
        return stats


# Context manager for automatic cleanup
class TempFileManager:
    """
    Context manager for automatic temporary file cleanup.
    Ensures files are cleaned up even if exceptions occur.
    """
    
    def __init__(self, cleanup_service: CleanupService, prefix: str = "resume_", suffix: str = ".pdf"):
        self.cleanup_service = cleanup_service
        self.prefix = prefix
        self.suffix = suffix
        self.temp_path = None
    
    def __enter__(self) -> str:
        """Create and return temporary file path."""
        self.temp_path = self.cleanup_service.get_temp_file_path(self.prefix, self.suffix)
        return self.temp_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary file on exit."""
        if self.temp_path:
            self.cleanup_service.cleanup_on_error(self.temp_path)