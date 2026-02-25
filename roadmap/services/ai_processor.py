"""
AI processing service coordinator and base interface
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseAIBackend(ABC):
    """
    Abstract base class for AI processing backends
    """
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available and properly configured"""
        pass
    
    @abstractmethod
    def process_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Process resume text and extract structured information
        
        Args:
            text: Raw text extracted from resume
            
        Returns:
            Dict containing extracted information with keys:
            - name: str or None
            - email: str or None  
            - phone: str or None
            - skills: List[str]
            - experience: List[Dict]
            - education: List[Dict]
            - confidence_score: float
        """
        pass
    
    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend"""
        pass


class AIProcessingError(Exception):
    """Custom exception for AI processing errors"""
    pass


class AIProcessor:
    """
    Coordinator service for different AI backends with fallback logic
    """
    
    def __init__(self):
        self._backends = {}
        self._backend_priority = ['gemini', 'spacy', 'rule_based']
        self._register_backends()
    
    def _register_backends(self):
        """Register available AI backends"""
        try:
            from .gemini_backend import GeminiBackend
            self._backends['gemini'] = GeminiBackend()
        except ImportError:
            logger.warning("Gemini backend not available")
        
        try:
            from .spacy_backend import SpacyBackend
            self._backends['spacy'] = SpacyBackend()
        except ImportError:
            logger.warning("spaCy backend not available")
        
        try:
            from .rule_based_backend import RuleBasedBackend
            self._backends['rule_based'] = RuleBasedBackend()
        except ImportError:
            logger.warning("Rule-based backend not available")
    
    def get_available_backends(self) -> List[str]:
        """
        Get list of available and properly configured AI processing backends
        
        Returns:
            List of backend names that are available
        """
        available = []
        for name, backend in self._backends.items():
            try:
                if backend.is_available():
                    available.append(name)
            except Exception as e:
                logger.warning(f"Backend {name} availability check failed: {e}")
        
        return available
    
    def process_resume_text(self, text: str, backend: str = 'auto') -> Dict[str, Any]:
        """
        Process resume text using specified AI backend with fallback logic
        
        Args:
            text: Raw text extracted from resume
            backend: Backend to use ('auto', 'gemini', 'spacy', 'rule_based')
            
        Returns:
            Dict containing extracted information and metadata
            
        Raises:
            AIProcessingError: If all backends fail
        """
        if not text or not text.strip():
            raise AIProcessingError("Empty or invalid text provided")
        
        backends_to_try = self._get_backends_to_try(backend)
        
        last_error = None
        for backend_name in backends_to_try:
            if backend_name not in self._backends:
                continue
                
            backend_instance = self._backends[backend_name]
            
            try:
                if not backend_instance.is_available():
                    logger.warning(f"Backend {backend_name} is not available, skipping")
                    continue
                
                logger.info(f"Attempting to process resume with {backend_name} backend")
                result = backend_instance.process_resume_text(text)
                
                # Add metadata about which backend was used
                result['processing_backend_used'] = backend_name
                result['fallback_used'] = backend != 'auto' and backend_name != backend
                
                logger.info(f"Successfully processed resume with {backend_name} backend")
                return result
                
            except Exception as e:
                last_error = e
                logger.error(f"Backend {backend_name} failed: {e}")
                continue
        
        # If we get here, all backends failed
        error_msg = f"All AI backends failed. Last error: {last_error}"
        logger.error(error_msg)
        raise AIProcessingError(error_msg)
    
    def _get_backends_to_try(self, backend: str) -> List[str]:
        """
        Get ordered list of backends to try based on requested backend
        
        Args:
            backend: Requested backend ('auto', 'gemini', 'spacy', 'rule_based')
            
        Returns:
            List of backend names in order of preference
        """
        if backend == 'auto':
            # Use priority order for auto selection
            return self._backend_priority.copy()
        elif backend in self._backends:
            # Try specific backend first, then fallback to others
            fallback_list = [backend]
            for fallback in self._backend_priority:
                if fallback != backend and fallback not in fallback_list:
                    fallback_list.append(fallback)
            return fallback_list
        else:
            # Unknown backend, use auto logic
            logger.warning(f"Unknown backend '{backend}', using auto selection")
            return self._backend_priority.copy()
    
    def get_backend_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed status information for all backends
        
        Returns:
            Dict with backend names as keys and status info as values
        """
        status = {}
        for name, backend in self._backends.items():
            try:
                is_available = backend.is_available()
                status[name] = {
                    'available': is_available,
                    'backend_name': backend.get_backend_name(),
                    'error': None
                }
            except Exception as e:
                status[name] = {
                    'available': False,
                    'backend_name': backend.get_backend_name() if hasattr(backend, 'get_backend_name') else name,
                    'error': str(e)
                }
        
        return status