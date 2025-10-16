"""
Audit logging utility for roadmap app
Provides secure logging functionality that sanitizes sensitive data
"""
import logging
import re
from typing import Any, Dict, List, Union


class AuditLogger:
    """
    Secure audit logger that sanitizes sensitive data before logging
    Requirements: 5.5
    """
    
    def __init__(self, logger_name: str = 'roadmap.audit'):
        """Initialize audit logger"""
        self.logger = logging.getLogger(logger_name)
        
        # Patterns for sensitive data that should be removed/masked
        self.sensitive_patterns = [
            # SSN patterns
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),
            (r'\b\d{9}\b', '[SSN_REDACTED]'),
            
            # Credit card patterns
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CREDIT_CARD_REDACTED]'),
            
            # Phone number patterns (be conservative)
            (r'\b\(\d{3}\)\s?\d{3}-\d{4}\b', '[PHONE_REDACTED]'),
            (r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE_REDACTED]'),
            
            # Password patterns
            (r'password["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', 'password: [REDACTED]'),
            (r'pwd["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', 'pwd: [REDACTED]'),
            
            # API keys and tokens
            (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}', 'api_key: [REDACTED]'),
            (r'["\']?token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}', 'token: [REDACTED]'),
        ]
        
        # Fields that should be completely removed from logs
        self.sensitive_fields = {
            'ssn', 'social_security_number', 'credit_card', 'credit_card_number',
            'password', 'pwd', 'api_key', 'token', 'secret', 'private_key'
        }
    
    def sanitize_for_logging(self, data: Any) -> Any:
        """
        Sanitize data for safe logging by removing/masking sensitive information
        
        Args:
            data: Data to sanitize (dict, list, string, or other)
            
        Returns:
            Sanitized version of the data
        """
        if isinstance(data, dict):
            return self._sanitize_dict(data)
        elif isinstance(data, list):
            return [self.sanitize_for_logging(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            # For other types, convert to string and sanitize
            return self._sanitize_string(str(data))
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data"""
        sanitized = {}
        
        for key, value in data.items():
            # Remove sensitive fields entirely
            if key.lower() in self.sensitive_fields:
                continue
                
            # Recursively sanitize values
            sanitized[key] = self.sanitize_for_logging(value)
        
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string content using regex patterns"""
        sanitized = text
        
        for pattern, replacement in self.sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def log_resume_processing(self, action: str, filename: str, 
                            processing_time: float = None, 
                            backend_used: str = None,
                            success: bool = True,
                            error_message: str = None):
        """
        Log resume processing activity safely
        
        Args:
            action: Action performed (e.g., 'upload', 'process', 'cleanup')
            filename: Original filename (will be sanitized)
            processing_time: Time taken for processing
            backend_used: AI backend used for processing
            success: Whether the operation was successful
            error_message: Error message if operation failed
        """
        log_data = {
            'action': action,
            'filename': self._sanitize_filename(filename),
            'success': success,
            'timestamp': self._get_timestamp()
        }
        
        if processing_time is not None:
            log_data['processing_time_seconds'] = round(processing_time, 3)
            
        if backend_used:
            log_data['backend_used'] = backend_used
            
        if error_message:
            log_data['error'] = self._sanitize_string(error_message)
        
        # Log at appropriate level
        if success:
            self.logger.info(f"Resume processing: {log_data}")
        else:
            self.logger.error(f"Resume processing failed: {log_data}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Log security-related events
        
        Args:
            event_type: Type of security event
            details: Event details (will be sanitized)
        """
        sanitized_details = self.sanitize_for_logging(details)
        
        log_data = {
            'event_type': event_type,
            'details': sanitized_details,
            'timestamp': self._get_timestamp()
        }
        
        self.logger.warning(f"Security event: {log_data}")
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """
        Log performance metrics safely
        
        Args:
            metrics: Performance metrics to log
        """
        # Performance metrics should generally be safe, but sanitize just in case
        sanitized_metrics = self.sanitize_for_logging(metrics)
        
        log_data = {
            'metrics': sanitized_metrics,
            'timestamp': self._get_timestamp()
        }
        
        self.logger.info(f"Performance metrics: {log_data}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for logging
        Keep the extension and general structure but remove potential sensitive info
        """
        if not filename:
            return '[NO_FILENAME]'
        
        # Remove directory paths for security
        import os
        base_filename = os.path.basename(filename)
        
        # Sanitize the filename content
        sanitized = self._sanitize_string(base_filename)
        
        return sanitized
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


# Global audit logger instance
audit_logger = AuditLogger()