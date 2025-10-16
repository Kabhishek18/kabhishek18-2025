"""
Views for the roadmap app (Resume Parser)
"""
import time
import logging
import json
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    ResumeUploadSerializer, 
    ResumeDataSerializer, 
    ErrorResponseSerializer,
    HealthCheckSerializer
)
from .services.pdf_extractor import PDFExtractor
from .services.ai_processor import AIProcessor, AIProcessingError
from .services.cleanup_service import CleanupService, TempFileManager
from .utils.exceptions import PDFExtractionError, InvalidFileFormatError
from api.authentication import get_authenticated_client, get_authenticated_api_key
from api.exceptions import APIException

logger = logging.getLogger(__name__)


class ResumeParseView(APIView):
    """
    API endpoint for parsing resume PDFs and extracting structured information
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pdf_extractor = PDFExtractor()
        self.ai_processor = AIProcessor()
        self.cleanup_service = CleanupService()
    
    @swagger_auto_schema(
        operation_description="Upload and parse a PDF resume to extract structured information",
        request_body=ResumeUploadSerializer,
        responses={
            200: openapi.Response(
                description="Resume parsed successfully",
                schema=ResumeDataSerializer
            ),
            400: openapi.Response(
                description="Invalid file format or validation error",
                schema=ErrorResponseSerializer
            ),
            413: openapi.Response(
                description="File size too large",
                schema=ErrorResponseSerializer
            ),
            422: openapi.Response(
                description="Processing error",
                schema=ErrorResponseSerializer
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=ErrorResponseSerializer
            )
        },
        tags=['Resume Parser']
    )
    def post(self, request):
        """
        Parse uploaded PDF resume and extract structured information
        """
        start_time = time.time()
        temp_file_path = None
        
        # Log API usage for authenticated clients
        client = get_authenticated_client(request)
        api_key = get_authenticated_api_key(request)
        
        if client:
            logger.info(f"Resume parsing request from client: {client.name} (ID: {client.client_id})")
        
        try:
            # Validate request data
            serializer = ResumeUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Invalid request data",
                            "details": serializer.errors
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            resume_file = validated_data['resume_file']
            processing_backend = validated_data.get('processing_backend', 'auto')
            include_raw_text = validated_data.get('include_raw_text', False)
            
            logger.info(f"Processing resume upload: {resume_file.name}, backend: {processing_backend}")
            
            # Use context manager for automatic cleanup
            with TempFileManager(self.cleanup_service) as temp_file_path:
                # Save uploaded file to temporary location
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in resume_file.chunks():
                        temp_file.write(chunk)
                
                logger.debug(f"Saved uploaded file to temporary location: {temp_file_path}")
                
                # Extract text from PDF
                try:
                    extracted_text = self.pdf_extractor.extract_text(temp_file_path)
                    logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
                except InvalidFileFormatError as e:
                    logger.error(f"Invalid file format: {e}")
                    return Response(
                        {
                            "error": {
                                "code": "INVALID_FILE_FORMAT",
                                "message": "Only PDF files are supported",
                                "details": {
                                    "file_name": resume_file.name,
                                    "error": str(e)
                                }
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except PDFExtractionError as e:
                    logger.error(f"PDF extraction failed: {e}")
                    return Response(
                        {
                            "error": {
                                "code": "PDF_EXTRACTION_ERROR",
                                "message": "Failed to extract text from PDF",
                                "details": {
                                    "file_name": resume_file.name,
                                    "error": str(e)
                                }
                            }
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
                
                # Process extracted text with AI
                try:
                    processed_data = self.ai_processor.process_resume_text(
                        extracted_text, 
                        processing_backend
                    )
                    logger.info(f"Successfully processed resume with {processed_data.get('processing_backend_used', 'unknown')} backend")
                except AIProcessingError as e:
                    logger.error(f"AI processing failed: {e}")
                    return Response(
                        {
                            "error": {
                                "code": "AI_PROCESSING_ERROR",
                                "message": "Failed to process resume text",
                                "details": {
                                    "backend_requested": processing_backend,
                                    "error": str(e)
                                }
                            }
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
                
                # Calculate processing time
                processing_time = time.time() - start_time
                processed_data['processing_time_seconds'] = round(processing_time, 2)
                
                # Add raw text if requested
                if include_raw_text:
                    processed_data['raw_text'] = extracted_text
                
                # Add any warnings
                warnings = []
                if processed_data.get('fallback_used', False):
                    warnings.append(f"Requested backend '{processing_backend}' failed, used fallback")
                
                if not processed_data.get('confidence_score') or processed_data.get('confidence_score', 0) < 0.5:
                    warnings.append("Low confidence in extracted data - manual review recommended")
                
                processed_data['warnings'] = warnings
                
                # Validate response data
                response_serializer = ResumeDataSerializer(data=processed_data)
                if not response_serializer.is_valid():
                    logger.error(f"Response validation failed: {response_serializer.errors}")
                    # Return the data anyway but log the validation issues
                    processed_data['validation_warnings'] = response_serializer.errors
                
                logger.info(f"Resume processing completed successfully in {processing_time:.2f} seconds")
                return Response(processed_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Ensure cleanup happens even on unexpected errors
            if temp_file_path:
                self.cleanup_service.cleanup_on_error(temp_file_path)
            
            logger.error(f"Unexpected error during resume processing: {e}", exc_info=True)
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred during processing",
                        "details": {
                            "error": str(e)
                        }
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """
    Health check endpoint for AI backends and system status
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ai_processor = AIProcessor()
        self.cleanup_service = CleanupService()
    
    @swagger_auto_schema(
        operation_description="Check the health and availability of AI backends and system resources",
        responses={
            200: openapi.Response(
                description="Health check completed",
                schema=HealthCheckSerializer
            ),
            503: openapi.Response(
                description="Service unavailable - critical backends down",
                schema=ErrorResponseSerializer
            )
        },
        tags=['Resume Parser']
    )
    def get(self, request):
        """
        Check system health and AI backend availability
        """
        try:
            # Check AI backend status
            backend_status = self.ai_processor.get_backend_status()
            available_backends = self.ai_processor.get_available_backends()
            
            # Get temporary directory statistics
            temp_stats = self.cleanup_service.get_temp_dir_stats()
            
            # Determine overall system status
            if not available_backends:
                overall_status = "degraded"
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif len(available_backends) < len(backend_status):
                overall_status = "degraded"
                status_code = status.HTTP_200_OK
            else:
                overall_status = "healthy"
                status_code = status.HTTP_200_OK
            
            # Build response
            health_data = {
                "status": overall_status,
                "backends": backend_status,
                "configuration": {
                    "available_backends": available_backends,
                    "total_backends": len(backend_status),
                    "temp_directory": temp_stats['temp_dir'],
                    "temp_files_count": temp_stats['file_count'],
                    "temp_files_size_mb": round(temp_stats['total_size_bytes'] / (1024 * 1024), 2),
                    "oldest_temp_file_age_minutes": temp_stats['oldest_file_age_minutes']
                }
            }
            
            # Validate response
            response_serializer = HealthCheckSerializer(data=health_data)
            if not response_serializer.is_valid():
                logger.warning(f"Health check response validation failed: {response_serializer.errors}")
            
            logger.info(f"Health check completed - Status: {overall_status}, Available backends: {len(available_backends)}")
            return Response(health_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return Response(
                {
                    "error": {
                        "code": "HEALTH_CHECK_ERROR",
                        "message": "Health check failed",
                        "details": {
                            "error": str(e)
                        }
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeUploadFormView(TemplateView):
    """
    HTML form view for resume upload and parsing
    """
    template_name = 'roadmap/resume_upload.html'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pdf_extractor = PDFExtractor()
        self.ai_processor = AIProcessor()
        self.cleanup_service = CleanupService()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get backend status for the form
        backend_status = self.ai_processor.get_backend_status()
        available_backends = self.ai_processor.get_available_backends()
        
        context.update({
            'backend_status': backend_status,
            'available_backends': available_backends,
            'backend_choices': [
                ('auto', 'Auto (Recommended)'),
                ('gemini', 'Gemini AI'),
                ('spacy', 'spaCy NLP'),
                ('rule_based', 'Rule-based'),
            ]
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle form submission via AJAX"""
        start_time = time.time()
        
        try:
            # Validate file upload
            resume_file = request.FILES.get('resume_file')
            if not resume_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No file uploaded'
                }, status=400)
            
            # Get form parameters
            processing_backend = request.POST.get('processing_backend', 'auto')
            include_raw_text = request.POST.get('include_raw_text') == 'on'
            
            logger.info(f"Processing resume upload: {resume_file.name}, backend: {processing_backend}")
            
            # Use context manager for automatic cleanup
            with TempFileManager(self.cleanup_service) as temp_file_path:
                # Save uploaded file to temporary location
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in resume_file.chunks():
                        temp_file.write(chunk)
                
                logger.debug(f"Saved uploaded file to temporary location: {temp_file_path}")
                
                # Extract text from PDF
                try:
                    extracted_text = self.pdf_extractor.extract_text(temp_file_path)
                    logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
                except InvalidFileFormatError as e:
                    logger.error(f"Invalid file format: {e}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Only PDF files are supported'
                    }, status=400)
                except PDFExtractionError as e:
                    logger.error(f"PDF extraction failed: {e}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to extract text from PDF: {str(e)}'
                    }, status=422)
                
                # Process extracted text with AI
                try:
                    processed_data = self.ai_processor.process_resume_text(
                        extracted_text, 
                        processing_backend
                    )
                    logger.info(f"Successfully processed resume with {processed_data.get('processing_backend_used', 'unknown')} backend")
                except AIProcessingError as e:
                    logger.error(f"AI processing failed: {e}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to process resume text: {str(e)}'
                    }, status=422)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                processed_data['processing_time_seconds'] = round(processing_time, 2)
                
                # Add raw text if requested
                if include_raw_text:
                    processed_data['raw_text'] = extracted_text
                
                # Add any warnings
                warnings = []
                if processed_data.get('fallback_used', False):
                    warnings.append(f"Requested backend '{processing_backend}' failed, used fallback")
                
                if not processed_data.get('confidence_score') or processed_data.get('confidence_score', 0) < 0.5:
                    warnings.append("Low confidence in extracted data - manual review recommended")
                
                processed_data['warnings'] = warnings
                
                logger.info(f"Resume processing completed successfully in {processing_time:.2f} seconds")
                return JsonResponse({
                    'success': True,
                    'data': processed_data
                })
        
        except Exception as e:
            logger.error(f"Unexpected error during resume processing: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'An unexpected error occurred: {str(e)}'
            }, status=500)