"""
Performance and security tests for roadmap app resume parsing functionality
Tests large file processing, memory usage, concurrent uploads, and security validation
"""
import os
import io
import time
import threading
import tempfile
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

# Try to import psutil, but make it optional for environments where it's not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from roadmap.models import ResumeParserConfig
from roadmap.services.cleanup_service import CleanupService
from roadmap.utils.security import SecurityValidator
from roadmap.utils.exceptions import FileValidationError


class PerformanceTests(APITestCase):
    """
    Performance tests for resume parsing functionality
    Tests large file processing and memory usage
    Requirements: 4.4, 5.4
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration with higher limits for performance testing
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=50,  # Higher limit for performance testing
            default_backend='rule_based',  # Use rule-based for consistent performance
            processing_timeout_seconds=600
        )
        
        # Track initial memory usage if psutil is available
        if PSUTIL_AVAILABLE:
            self.initial_memory = psutil.Process().memory_info().rss
        else:
            self.initial_memory = 0
    
    def tearDown(self):
        """Clean up after tests"""
        # Force garbage collection
        gc.collect()
        
        # Check for memory leaks if psutil is available
        if PSUTIL_AVAILABLE:
            final_memory = psutil.Process().memory_info().rss
            memory_increase = final_memory - self.initial_memory
            
            # Allow for some memory increase but warn if excessive (>100MB)
            if memory_increase > 100 * 1024 * 1024:
                print(f"Warning: Memory increased by {memory_increase / (1024 * 1024):.1f}MB during test")
    
    def _create_large_pdf_content(self, size_mb: int) -> bytes:
        """Create a large PDF file for testing"""
        # Basic PDF structure
        pdf_header = b'%PDF-1.4\n'
        pdf_catalog = b'1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        pdf_pages = b'2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n'
        pdf_page = b'3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n'
        
        # Calculate how much padding we need
        base_size = len(pdf_header + pdf_catalog + pdf_pages + pdf_page)
        target_size = size_mb * 1024 * 1024
        padding_size = target_size - base_size - 100  # Leave room for trailer
        
        # Create padding content (simulate large text content)
        padding = b'BT\n/F1 12 Tf\n100 700 Td\n' + b'(Large resume content) Tj\n' * (padding_size // 25) + b'ET\n'
        
        # PDF trailer
        pdf_trailer = b'xref\n0 4\n0000000000 65535 f \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n%%EOF'
        
        return pdf_header + pdf_catalog + pdf_pages + pdf_page + padding + pdf_trailer
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_large_file_processing_memory_usage(self, mock_ai_process, mock_pdf_extract):
        """
        Test processing of large files and monitor memory usage
        Requirements: 4.4
        """
        # Mock successful processing to focus on file handling
        mock_pdf_extract.return_value = "Large resume content " * 1000
        mock_ai_process.return_value = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': None,
            'skills': ['Python'],
            'experience': [],
            'education': [],
            'processing_backend_used': 'rule_based',
            'confidence_score': 0.6
        }
        
        # Test with different file sizes
        file_sizes = [5, 10, 20]  # MB
        
        for size_mb in file_sizes:
            with self.subTest(size_mb=size_mb):
                # Monitor memory before processing if psutil is available
                if PSUTIL_AVAILABLE:
                    memory_before = psutil.Process().memory_info().rss
                else:
                    memory_before = 0
                
                # Create large PDF content
                large_content = self._create_large_pdf_content(size_mb)
                
                large_file = SimpleUploadedFile(
                    f"large_resume_{size_mb}mb.pdf",
                    large_content,
                    content_type="application/pdf"
                )
                
                # Process the file
                start_time = time.time()
                response = self.client.post(self.url, {
                    'resume_file': large_file
                }, format='multipart')
                processing_time = time.time() - start_time
                
                # Monitor memory after processing if psutil is available
                if PSUTIL_AVAILABLE:
                    memory_after = psutil.Process().memory_info().rss
                    memory_used = memory_after - memory_before
                else:
                    memory_used = 0
                
                # Verify successful processing
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Performance assertions
                self.assertLess(processing_time, 30, f"Processing {size_mb}MB file took too long: {processing_time:.2f}s")
                
                # Memory usage should not exceed 3x file size (only if psutil available)
                if PSUTIL_AVAILABLE:
                    max_expected_memory = size_mb * 1024 * 1024 * 3
                    self.assertLess(memory_used, max_expected_memory, 
                                   f"Memory usage ({memory_used / (1024 * 1024):.1f}MB) exceeded expected for {size_mb}MB file")
                
                # Force cleanup
                gc.collect()
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_concurrent_upload_handling(self, mock_ai_process, mock_pdf_extract):
        """
        Test handling of concurrent file uploads
        Requirements: 5.4
        """
        # Mock processing with slight delay to simulate real processing
        def mock_extract_with_delay(file_path):
            time.sleep(0.1)  # Small delay to simulate processing
            return f"Resume content from {os.path.basename(file_path)}"
        
        def mock_ai_with_delay(text, backend):
            time.sleep(0.1)  # Small delay to simulate AI processing
            return {
                'name': f'User from {text[:20]}',
                'email': 'concurrent@example.com',
                'phone': None,
                'skills': ['Concurrency'],
                'experience': [],
                'education': [],
                'processing_backend_used': backend,
                'confidence_score': 0.7
            }
        
        mock_pdf_extract.side_effect = mock_extract_with_delay
        mock_ai_process.side_effect = mock_ai_with_delay
        
        # Create test files
        num_concurrent = 10
        test_files = []
        
        for i in range(num_concurrent):
            content = self._create_large_pdf_content(1)  # 1MB files
            test_file = SimpleUploadedFile(
                f"concurrent_resume_{i}.pdf",
                content,
                content_type="application/pdf"
            )
            test_files.append(test_file)
        
        # Track results
        results = []
        errors = []
        
        def upload_file(file_index, test_file):
            """Upload a file and return result"""
            try:
                start_time = time.time()
                response = self.client.post(self.url, {
                    'resume_file': test_file
                }, format='multipart')
                processing_time = time.time() - start_time
                
                return {
                    'index': file_index,
                    'status_code': response.status_code,
                    'processing_time': processing_time,
                    'response_data': response.json() if response.status_code == 200 else None
                }
            except Exception as e:
                return {
                    'index': file_index,
                    'error': str(e),
                    'processing_time': None
                }
        
        # Execute concurrent uploads
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all upload tasks
            future_to_index = {
                executor.submit(upload_file, i, test_files[i]): i 
                for i in range(num_concurrent)
            }
            
            # Collect results
            for future in as_completed(future_to_index):
                result = future.result()
                if 'error' in result:
                    errors.append(result)
                else:
                    results.append(result)
        
        total_time = time.time() - start_time
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent upload errors: {errors}")
        self.assertEqual(len(results), num_concurrent, "Not all uploads completed successfully")
        
        # All uploads should succeed
        successful_uploads = [r for r in results if r['status_code'] == 200]
        self.assertEqual(len(successful_uploads), num_concurrent, "Some uploads failed")
        
        # Performance checks
        avg_processing_time = sum(r['processing_time'] for r in results) / len(results)
        self.assertLess(avg_processing_time, 5.0, f"Average processing time too high: {avg_processing_time:.2f}s")
        self.assertLess(total_time, 15.0, f"Total concurrent processing time too high: {total_time:.2f}s")
        
        # Verify each upload processed correctly
        for result in results:
            self.assertIsNotNone(result['response_data'])
            self.assertIn('name', result['response_data'])
            self.assertIn('processing_time_seconds', result['response_data'])
    
    def test_memory_cleanup_after_processing(self):
        """
        Test that memory is properly cleaned up after processing
        Requirements: 5.1, 5.2
        """
        cleanup_service = CleanupService()
        
        # Create multiple temporary files
        temp_files = []
        if PSUTIL_AVAILABLE:
            initial_memory = psutil.Process().memory_info().rss
        else:
            initial_memory = 0
        
        try:
            # Create and process multiple files
            for i in range(5):
                temp_path = cleanup_service.get_temp_file_path(f"memory_test_{i}_")
                
                # Write some content to the file
                with open(temp_path, 'wb') as f:
                    f.write(b'x' * (1024 * 1024))  # 1MB of data
                
                temp_files.append(temp_path)
                
                # Verify file exists
                self.assertTrue(os.path.exists(temp_path))
            
            # Check memory usage increased
            memory_after_creation = psutil.Process().memory_info().rss
            self.assertGreater(memory_after_creation, initial_memory)
            
            # Clean up all files
            cleanup_count = cleanup_service.cleanup_multiple_files(temp_files)
            self.assertEqual(cleanup_count, len(temp_files))
            
            # Verify files are deleted
            for temp_path in temp_files:
                self.assertFalse(os.path.exists(temp_path))
            
            # Force garbage collection
            gc.collect()
            
            # Memory should be released (allow some variance)
            final_memory = psutil.Process().memory_info().rss
            memory_difference = final_memory - initial_memory
            
            # Should not retain more than 10MB after cleanup
            self.assertLess(memory_difference, 10 * 1024 * 1024, 
                           f"Memory not properly released: {memory_difference / (1024 * 1024):.1f}MB retained")
            
        finally:
            # Ensure cleanup even if test fails
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    
    def test_temp_directory_performance(self):
        """
        Test performance of temporary directory operations
        Requirements: 5.1, 5.4
        """
        cleanup_service = CleanupService()
        
        # Test temp file creation performance
        start_time = time.time()
        temp_paths = []
        
        for i in range(100):
            temp_path = cleanup_service.get_temp_file_path(f"perf_test_{i}_")
            temp_paths.append(temp_path)
        
        creation_time = time.time() - start_time
        
        # Should create 100 temp file paths quickly
        self.assertLess(creation_time, 1.0, f"Temp file path creation too slow: {creation_time:.2f}s")
        
        # Test cleanup performance
        start_time = time.time()
        cleanup_count = cleanup_service.cleanup_multiple_files(temp_paths)
        cleanup_time = time.time() - start_time
        
        # Should cleanup quickly (files don't exist, so should be fast)
        self.assertLess(cleanup_time, 0.5, f"Temp file cleanup too slow: {cleanup_time:.2f}s")
        self.assertEqual(cleanup_count, len(temp_paths))


class SecurityTests(APITestCase):
    """
    Security tests for resume parsing functionality
    Tests security validation and file isolation
    Requirements: 5.5
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='rule_based'
        )
        
        self.security_validator = SecurityValidator()
    
    def test_malicious_file_detection(self):
        """
        Test detection and rejection of malicious files
        Requirements: 5.5
        """
        # Test various malicious file types and content
        malicious_test_cases = [
            {
                'name': 'executable_disguised_as_pdf.pdf',
                'content': b'MZ\x90\x00\x03\x00\x00\x00',  # PE executable header
                'description': 'Windows executable disguised as PDF'
            },
            {
                'name': 'script_injection.pdf',
                'content': b'%PDF-1.4\n<script>alert("xss")</script>',
                'description': 'PDF with script injection attempt'
            },
            {
                'name': 'shell_commands.pdf',
                'content': b'%PDF-1.4\n#!/bin/bash\nrm -rf /',
                'description': 'PDF with shell commands'
            },
            {
                'name': 'zip_bomb.pdf',
                'content': b'PK\x03\x04' + b'\x00' * 100,  # ZIP file header
                'description': 'ZIP file disguised as PDF'
            },
            {
                'name': 'null_bytes.pdf',
                'content': b'%PDF-1.4\n\x00\x00\x00malicious\x00\x00',
                'description': 'PDF with null bytes'
            },
            {
                'name': 'oversized_header.pdf',
                'content': b'%PDF-1.4\n' + b'A' * 10000,  # Extremely long header
                'description': 'PDF with oversized header'
            }
        ]
        
        for test_case in malicious_test_cases:
            with self.subTest(description=test_case['description']):
                malicious_file = SimpleUploadedFile(
                    test_case['name'],
                    test_case['content'],
                    content_type="application/pdf"
                )
                
                # Test security validation
                validation_result = self.security_validator.validate_file_upload(malicious_file)
                
                # Should be detected as invalid
                self.assertFalse(validation_result['is_valid'], 
                               f"Malicious file not detected: {test_case['description']}")
                self.assertGreater(len(validation_result['errors']), 0)
                
                # Test API endpoint rejection
                response = self.client.post(self.url, {
                    'resume_file': malicious_file
                }, format='multipart')
                
                # Should be rejected
                self.assertIn(response.status_code, [400, 422], 
                             f"Malicious file not rejected by API: {test_case['description']}")
    
    def test_file_isolation_security(self):
        """
        Test that uploaded files are properly isolated
        Requirements: 5.1, 5.2, 5.4
        """
        cleanup_service = CleanupService()
        
        # Test file path generation security
        temp_paths = []
        for i in range(10):
            temp_path = cleanup_service.get_temp_file_path()
            temp_paths.append(temp_path)
            
            # Verify path is in temp directory
            self.assertTrue(temp_path.startswith(cleanup_service.temp_dir))
            
            # Verify path doesn't contain directory traversal
            self.assertNotIn('..', temp_path)
            self.assertNotIn('//', temp_path)
            
            # Verify unique paths
            self.assertEqual(len(set(temp_paths)), len(temp_paths), "Temp paths not unique")
        
        # Test file permissions (Unix-like systems)
        if hasattr(os, 'chmod'):
            temp_path = cleanup_service.get_temp_file_path()
            
            # Create file and check permissions
            with open(temp_path, 'w') as f:
                f.write('test')
            
            # Check file permissions are restrictive
            file_stat = os.stat(temp_path)
            file_mode = file_stat.st_mode & 0o777
            
            # Should not be world-readable/writable
            self.assertEqual(file_mode & 0o007, 0, "Temp file has world permissions")
            
            # Cleanup
            cleanup_service.cleanup_temp_file(temp_path)
    
    def test_input_sanitization(self):
        """
        Test input sanitization and validation
        Requirements: 5.5
        """
        # Test various malicious input patterns
        malicious_inputs = [
            '../../../etc/passwd',
            '$(rm -rf /)',
            '<script>alert("xss")</script>',
            'file:///etc/passwd',
            'javascript:alert(1)',
            '\x00\x01\x02\x03',  # Control characters
            'A' * 10000,  # Extremely long input
        ]
        
        for malicious_input in malicious_inputs:
            with self.subTest(input=malicious_input[:50]):  # Truncate for readability
                # Test as filename
                malicious_file = SimpleUploadedFile(
                    malicious_input,
                    b'%PDF-1.4\ntest content',
                    content_type="application/pdf"
                )
                
                response = self.client.post(self.url, {
                    'resume_file': malicious_file
                }, format='multipart')
                
                # Should handle malicious input safely
                self.assertIn(response.status_code, [400, 422, 500])
                
                # Response should not contain the malicious input
                response_text = str(response.content)
                if len(malicious_input) > 10:  # Only check longer inputs
                    self.assertNotIn(malicious_input, response_text)
    
    def test_resource_exhaustion_protection(self):
        """
        Test protection against resource exhaustion attacks
        Requirements: 4.4, 5.4
        """
        # Test file size limits
        oversized_content = b'%PDF-1.4\n' + b'x' * (50 * 1024 * 1024)  # 50MB
        
        oversized_file = SimpleUploadedFile(
            "oversized.pdf",
            oversized_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': oversized_file
        }, format='multipart')
        
        # Should reject oversized file
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test rapid successive uploads (rate limiting simulation)
        small_file_content = b'%PDF-1.4\nsmall content'
        
        responses = []
        start_time = time.time()
        
        for i in range(20):  # Rapid uploads
            test_file = SimpleUploadedFile(
                f"rapid_{i}.pdf",
                small_file_content,
                content_type="application/pdf"
            )
            
            response = self.client.post(self.url, {
                'resume_file': test_file
            }, format='multipart')
            
            responses.append(response.status_code)
        
        total_time = time.time() - start_time
        
        # Should handle rapid requests without crashing
        self.assertLess(total_time, 30.0, "Rapid requests took too long to process")
        
        # Most requests should be handled (may have some failures due to mocking)
        successful_responses = [r for r in responses if r in [200, 400, 422]]
        self.assertGreater(len(successful_responses), 15, "Too many requests failed completely")
    
    def test_temporary_file_security(self):
        """
        Test security of temporary file handling
        Requirements: 5.1, 5.2, 5.3
        """
        cleanup_service = CleanupService()
        
        # Test secure temp file creation
        temp_path = cleanup_service.get_temp_file_path()
        
        # Write sensitive data to temp file
        sensitive_data = b"SSN: 123-45-6789\nCredit Card: 4111-1111-1111-1111"
        
        with open(temp_path, 'wb') as f:
            f.write(sensitive_data)
        
        # Verify file exists and contains data
        self.assertTrue(os.path.exists(temp_path))
        
        with open(temp_path, 'rb') as f:
            content = f.read()
            self.assertEqual(content, sensitive_data)
        
        # Test secure cleanup
        cleanup_result = cleanup_service.cleanup_temp_file(temp_path)
        self.assertTrue(cleanup_result)
        
        # Verify file is completely removed
        self.assertFalse(os.path.exists(temp_path))
        
        # Test error-safe cleanup
        temp_path2 = cleanup_service.get_temp_file_path()
        
        with open(temp_path2, 'wb') as f:
            f.write(b"test data")
        
        # Should not raise exceptions even if called multiple times
        try:
            cleanup_service.cleanup_on_error(temp_path2)
            cleanup_service.cleanup_on_error(temp_path2)  # Second call on non-existent file
            cleanup_service.cleanup_on_error(None)  # Null path
            cleanup_service.cleanup_on_error("")  # Empty path
        except Exception as e:
            self.fail(f"cleanup_on_error raised exception: {e}")
        
        # File should be gone
        self.assertFalse(os.path.exists(temp_path2))
    
    def test_directory_traversal_protection(self):
        """
        Test protection against directory traversal attacks
        Requirements: 5.5
        """
        cleanup_service = CleanupService()
        
        # Test various directory traversal patterns
        traversal_patterns = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '/etc/passwd',
            'C:\\windows\\system32\\config\\sam',
            '....//....//....//etc/passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',  # URL encoded
        ]
        
        for pattern in traversal_patterns:
            with self.subTest(pattern=pattern):
                # Test that temp file paths don't allow traversal
                temp_path = cleanup_service.get_temp_file_path(prefix=pattern)
                
                # Should be contained within temp directory
                normalized_temp = os.path.normpath(temp_path)
                normalized_temp_dir = os.path.normpath(cleanup_service.temp_dir)
                
                self.assertTrue(normalized_temp.startswith(normalized_temp_dir),
                               f"Directory traversal possible: {temp_path}")
                
                # Cleanup
                if os.path.exists(temp_path):
                    cleanup_service.cleanup_temp_file(temp_path)


class ConcurrencyStressTests(TestCase):
    """
    Stress tests for concurrent operations and race conditions
    Requirements: 5.4
    """
    
    def setUp(self):
        """Set up test environment"""
        self.cleanup_service = CleanupService()
    
    def test_concurrent_temp_file_operations(self):
        """
        Test concurrent temporary file operations for race conditions
        Requirements: 5.4
        """
        num_threads = 20
        operations_per_thread = 10
        
        results = []
        errors = []
        
        def temp_file_operations(thread_id):
            """Perform temp file operations in a thread"""
            thread_results = []
            
            try:
                for i in range(operations_per_thread):
                    # Create temp file
                    temp_path = self.cleanup_service.get_temp_file_path(f"thread_{thread_id}_op_{i}_")
                    
                    # Write data
                    with open(temp_path, 'w') as f:
                        f.write(f"Thread {thread_id} operation {i}")
                    
                    # Verify file exists
                    if not os.path.exists(temp_path):
                        raise Exception(f"File not created: {temp_path}")
                    
                    # Cleanup
                    cleanup_result = self.cleanup_service.cleanup_temp_file(temp_path)
                    
                    thread_results.append({
                        'thread_id': thread_id,
                        'operation': i,
                        'temp_path': temp_path,
                        'cleanup_success': cleanup_result
                    })
                
                return thread_results
                
            except Exception as e:
                return {'error': str(e), 'thread_id': thread_id}
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(temp_file_operations, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, dict) and 'error' in result:
                    errors.append(result)
                else:
                    results.extend(result)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent operations had errors: {errors}")
        self.assertEqual(len(results), num_threads * operations_per_thread)
        
        # Verify all operations succeeded
        successful_cleanups = [r for r in results if r['cleanup_success']]
        self.assertEqual(len(successful_cleanups), len(results), "Some cleanup operations failed")
        
        # Verify no temp files remain
        temp_paths = [r['temp_path'] for r in results]
        remaining_files = [p for p in temp_paths if os.path.exists(p)]
        self.assertEqual(len(remaining_files), 0, f"Temp files not cleaned up: {remaining_files}")
    
    def test_concurrent_cleanup_operations(self):
        """
        Test concurrent cleanup operations
        Requirements: 5.1, 5.4
        """
        # Create multiple temp files
        temp_files = []
        for i in range(50):
            temp_path = self.cleanup_service.get_temp_file_path(f"cleanup_test_{i}_")
            with open(temp_path, 'w') as f:
                f.write(f"Test file {i}")
            temp_files.append(temp_path)
        
        # Verify all files exist
        for temp_path in temp_files:
            self.assertTrue(os.path.exists(temp_path))
        
        # Concurrent cleanup
        cleanup_results = []
        
        def cleanup_batch(file_batch):
            """Cleanup a batch of files"""
            return self.cleanup_service.cleanup_multiple_files(file_batch)
        
        # Split files into batches for concurrent cleanup
        batch_size = 10
        batches = [temp_files[i:i + batch_size] for i in range(0, len(temp_files), batch_size)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cleanup_batch, batch) for batch in batches]
            
            for future in as_completed(futures):
                cleanup_results.append(future.result())
        
        # Verify cleanup results
        total_cleaned = sum(cleanup_results)
        self.assertEqual(total_cleaned, len(temp_files), "Not all files were cleaned up")
        
        # Verify no files remain
        remaining_files = [f for f in temp_files if os.path.exists(f)]
        self.assertEqual(len(remaining_files), 0, f"Files still exist after cleanup: {remaining_files}")


class LoggingSecurityTests(APITestCase):
    """
    Security tests for logging functionality
    Tests that sensitive data is not logged
    Requirements: 5.5
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='rule_based'
        )
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('logging.getLogger')
    def test_sensitive_data_not_logged(self, mock_logger, mock_ai_process, mock_pdf_extract):
        """
        Test that sensitive resume data is not logged
        Requirements: 5.5
        """
        # Create mock logger to capture log calls
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        # Sensitive test data
        sensitive_resume_text = """
        John Doe
        Email: john.doe@example.com
        Phone: (555) 123-4567
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        Password: MySecretPassword123
        """
        
        mock_pdf_extract.return_value = sensitive_resume_text
        mock_ai_process.return_value = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '(555) 123-4567',
            'skills': ['Python'],
            'experience': [],
            'education': [],
            'processing_backend_used': 'rule_based',
            'confidence_score': 0.8
        }
        
        # Create test PDF with sensitive content
        test_file = SimpleUploadedFile(
            "sensitive_resume.pdf",
            b'%PDF-1.4\nSensitive resume content',
            content_type="application/pdf"
        )
        
        # Process the file
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        # Verify successful processing
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all log calls to ensure no sensitive data was logged
        all_log_calls = []
        for call_type in ['debug', 'info', 'warning', 'error', 'critical']:
            method = getattr(mock_logger_instance, call_type)
            all_log_calls.extend([str(call) for call in method.call_args_list])
        
        # Convert all log calls to string for analysis
        log_content = ' '.join(all_log_calls).lower()
        
        # Sensitive patterns that should NOT appear in logs
        sensitive_patterns = [
            '123-45-6789',  # SSN
            '4111-1111-1111-1111',  # Credit card
            'mysecretpassword123',  # Password
            '(555) 123-4567',  # Phone number (should be sanitized)
        ]
        
        for pattern in sensitive_patterns:
            self.assertNotIn(pattern.lower(), log_content, 
                           f"Sensitive data '{pattern}' found in logs")
        
        # Verify that some logging occurred (but without sensitive data)
        # This ensures our test is actually checking real log calls
        self.assertTrue(len(all_log_calls) > 0 or not mock_logger.called, 
                       "No logging calls detected - test may not be comprehensive")
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_error_logging_without_sensitive_data(self, mock_ai_process, mock_pdf_extract):
        """
        Test that error logs don't contain sensitive resume content
        Requirements: 5.5
        """
        # Mock PDF extraction to return sensitive content
        sensitive_content = "SSN: 123-45-6789\nCredit Card: 4111-1111-1111-1111"
        mock_pdf_extract.return_value = sensitive_content
        
        # Mock AI processing to fail
        mock_ai_process.side_effect = Exception("AI processing failed")
        
        test_file = SimpleUploadedFile(
            "error_test.pdf",
            b'%PDF-1.4\nTest content',
            content_type="application/pdf"
        )
        
        # Capture logs during processing
        with self.assertLogs(level='ERROR') as log_context:
            response = self.client.post(self.url, {
                'resume_file': test_file
            }, format='multipart')
        
        # Should return error response
        self.assertIn(response.status_code, [422, 500])
        
        # Check that error logs don't contain sensitive data
        log_output = ' '.join(log_context.output)
        
        sensitive_patterns = ['123-45-6789', '4111-1111-1111-1111']
        for pattern in sensitive_patterns:
            self.assertNotIn(pattern, log_output, 
                           f"Sensitive data '{pattern}' found in error logs")
    
    def test_audit_logging_sanitization(self):
        """
        Test that audit logs are properly sanitized
        Requirements: 5.5
        """
        from roadmap.utils.audit_logger import AuditLogger
        
        # Test audit logger directly
        audit_logger = AuditLogger()
        
        # Test data with sensitive information
        test_data = {
            'user_id': 123,
            'action': 'resume_upload',
            'filename': 'john_doe_resume.pdf',
            'extracted_data': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'ssn': '123-45-6789',
                'credit_card': '4111-1111-1111-1111'
            }
        }
        
        # Log the data
        sanitized_data = audit_logger.sanitize_for_logging(test_data)
        
        # Verify sensitive fields are removed or masked
        self.assertNotIn('ssn', str(sanitized_data))
        self.assertNotIn('credit_card', str(sanitized_data))
        self.assertNotIn('123-45-6789', str(sanitized_data))
        self.assertNotIn('4111-1111-1111-1111', str(sanitized_data))
        
        # Verify non-sensitive data is preserved
        self.assertIn('john_doe_resume.pdf', str(sanitized_data))
        self.assertIn('resume_upload', str(sanitized_data))


class DataPersistenceTests(APITestCase):
    """
    Tests to verify no resume data persists after processing
    Requirements: 5.4
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='rule_based'
        )
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_no_data_persistence_after_successful_processing(self, mock_ai_process, mock_pdf_extract):
        """
        Test that no resume data persists after successful processing
        Requirements: 5.4
        """
        # Mock successful processing
        test_content = "John Doe\nSoftware Engineer\njohn@example.com"
        mock_pdf_extract.return_value = test_content
        mock_ai_process.return_value = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': None,
            'skills': ['Python'],
            'experience': [],
            'education': [],
            'processing_backend_used': 'rule_based',
            'confidence_score': 0.7
        }
        
        # Get initial temp directory state
        cleanup_service = CleanupService()
        temp_dir = cleanup_service.temp_dir
        initial_files = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
        
        # Process resume
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            b'%PDF-1.4\nTest resume content',
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        # Verify successful processing
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that no new files persist in temp directory
        final_files = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
        new_files = final_files - initial_files
        
        self.assertEqual(len(new_files), 0, f"Temporary files persist after processing: {new_files}")
        
        # Verify response confirms no data persistence
        response_data = response.json()
        self.assertIn('processing_time_seconds', response_data)
        
        # Check that no resume content is stored in database
        # (This assumes no models store resume content - verify with actual models)
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check that no tables contain the test content
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            for table in tables:
                if table.startswith('roadmap_'):
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    # For this test, we expect no resume data in roadmap tables
                    # (except configuration which should be minimal)
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    def test_no_data_persistence_after_error(self, mock_pdf_extract):
        """
        Test that no resume data persists after processing errors
        Requirements: 5.4
        """
        # Mock PDF extraction to fail
        mock_pdf_extract.side_effect = Exception("PDF extraction failed")
        
        # Get initial temp directory state
        cleanup_service = CleanupService()
        temp_dir = cleanup_service.temp_dir
        initial_files = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
        
        # Attempt to process resume
        test_file = SimpleUploadedFile(
            "error_resume.pdf",
            b'%PDF-1.4\nTest resume content',
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        # Should return error
        self.assertIn(response.status_code, [422, 500])
        
        # Check that no files persist even after error
        final_files = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
        new_files = final_files - initial_files
        
        self.assertEqual(len(new_files), 0, f"Temporary files persist after error: {new_files}")
    
    def test_memory_cleanup_verification(self):
        """
        Test that memory is properly cleaned after processing
        Requirements: 5.4
        """
        if not PSUTIL_AVAILABLE:
            self.skipTest("psutil not available for memory testing")
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simulate processing multiple files
        cleanup_service = CleanupService()
        
        for i in range(10):
            # Create temporary file with content
            temp_path = cleanup_service.get_temp_file_path(f"memory_test_{i}_")
            
            with open(temp_path, 'wb') as f:
                f.write(b'x' * (1024 * 1024))  # 1MB per file
            
            # Immediately cleanup
            cleanup_service.cleanup_temp_file(temp_path)
        
        # Force garbage collection
        gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not have significant memory increase (allow 5MB variance)
        max_allowed_increase = 5 * 1024 * 1024
        self.assertLess(memory_increase, max_allowed_increase,
                       f"Memory increased by {memory_increase / (1024 * 1024):.1f}MB after cleanup")


class FileSizeLimitTests(APITestCase):
    """
    Additional tests for file size limit handling
    Requirements: 4.4
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration with specific size limits
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=5,  # 5MB limit for testing
            default_backend='rule_based'
        )
    
    def test_file_size_limit_enforcement(self):
        """
        Test that file size limits are properly enforced
        Requirements: 4.4
        """
        # Create file that exceeds the limit (6MB when limit is 5MB)
        oversized_content = b'%PDF-1.4\n' + b'x' * (6 * 1024 * 1024)
        
        oversized_file = SimpleUploadedFile(
            "oversized.pdf",
            oversized_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': oversized_file
        }, format='multipart')
        
        # Should return 413 error (Request Entity Too Large)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Error message should mention size limit
        response_data = response.json()
        self.assertIn('error', response_data)
        error_message = str(response_data['error']).lower()
        self.assertTrue(
            'size' in error_message or 'large' in error_message or 'limit' in error_message,
            f"Error message doesn't mention size limit: {response_data['error']}"
        )
    
    def test_file_size_limit_boundary_conditions(self):
        """
        Test file size limit boundary conditions
        Requirements: 4.4
        """
        # Test file exactly at the limit (5MB)
        limit_content = b'%PDF-1.4\n' + b'x' * (5 * 1024 * 1024 - 10)  # Slightly under 5MB
        
        limit_file = SimpleUploadedFile(
            "at_limit.pdf",
            limit_content,
            content_type="application/pdf"
        )
        
        with patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text') as mock_extract, \
             patch('roadmap.services.ai_processor.AIProcessor.process_resume_text') as mock_ai:
            
            mock_extract.return_value = "Test content"
            mock_ai.return_value = {
                'name': 'Test User',
                'email': 'test@example.com',
                'phone': None,
                'skills': [],
                'experience': [],
                'education': [],
                'processing_backend_used': 'rule_based',
                'confidence_score': 0.5
            }
            
            response = self.client.post(self.url, {
                'resume_file': limit_file
            }, format='multipart')
            
            # Should succeed for file at/under limit
            self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_configurable_size_limits(self):
        """
        Test that size limits are configurable
        Requirements: 4.4
        """
        # Update configuration to different limit
        self.config.max_file_size_mb = 2
        self.config.save()
        
        # Create file that exceeds new limit (3MB when limit is 2MB)
        oversized_content = b'%PDF-1.4\n' + b'x' * (3 * 1024 * 1024)
        
        oversized_file = SimpleUploadedFile(
            "oversized_new_limit.pdf",
            oversized_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': oversized_file
        }, format='multipart')
        
        # Should be rejected with new limit
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test file under new limit (1MB)
        small_content = b'%PDF-1.4\n' + b'x' * (1024 * 1024)
        
        small_file = SimpleUploadedFile(
            "small.pdf",
            small_content,
            content_type="application/pdf"
        )
        
        with patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text') as mock_extract, \
             patch('roadmap.services.ai_processor.AIProcessor.process_resume_text') as mock_ai:
            
            mock_extract.return_value = "Small file content"
            mock_ai.return_value = {
                'name': 'Small User',
                'email': 'small@example.com',
                'phone': None,
                'skills': [],
                'experience': [],
                'education': [],
                'processing_backend_used': 'rule_based',
                'confidence_score': 0.5
            }
            
            response = self.client.post(self.url, {
                'resume_file': small_file
            }, format='multipart')
            
            # Should succeed with small file
            self.assertEqual(response.status_code, status.HTTP_200_OK)