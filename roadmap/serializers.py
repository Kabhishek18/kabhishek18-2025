"""
Serializers for the roadmap app (Resume Parser)
"""
from rest_framework import serializers
from .utils.validators import validate_pdf_file, validate_file_size


class ExperienceSerializer(serializers.Serializer):
    """
    Serializer for work experience data
    """
    job_title = serializers.CharField(max_length=200, allow_null=True, required=False)
    company = serializers.CharField(max_length=200, allow_null=True, required=False)
    start_date = serializers.CharField(max_length=50, allow_null=True, required=False)
    end_date = serializers.CharField(max_length=50, allow_null=True, required=False)
    description = serializers.CharField(allow_null=True, required=False)
    location = serializers.CharField(max_length=200, allow_null=True, required=False)
    is_current = serializers.BooleanField(default=False, required=False)


class EducationSerializer(serializers.Serializer):
    """
    Serializer for education data
    """
    degree = serializers.CharField(max_length=200, allow_null=True, required=False)
    institution = serializers.CharField(max_length=200, allow_null=True, required=False)
    field_of_study = serializers.CharField(max_length=200, allow_null=True, required=False)
    start_date = serializers.CharField(max_length=50, allow_null=True, required=False)
    end_date = serializers.CharField(max_length=50, allow_null=True, required=False)
    gpa = serializers.CharField(max_length=10, allow_null=True, required=False)
    location = serializers.CharField(max_length=200, allow_null=True, required=False)


class SkillCategorySerializer(serializers.Serializer):
    """
    Serializer for categorized skills
    """
    category = serializers.CharField(max_length=100)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        allow_empty=True
    )


class ResumeUploadSerializer(serializers.Serializer):
    """
    Serializer for resume upload requests with file validation
    """
    BACKEND_CHOICES = [
        ('auto', 'Auto (Gemini -> spaCy -> Rule-based)'),
        ('gemini', 'Gemini AI'),
        ('spacy', 'spaCy NLP'),
        ('rule_based', 'Rule-based'),
    ]
    
    resume_file = serializers.FileField(
        validators=[validate_pdf_file, validate_file_size],
        help_text="PDF file containing the resume to parse"
    )
    
    processing_backend = serializers.ChoiceField(
        choices=BACKEND_CHOICES,
        default='auto',
        required=False,
        help_text="AI backend to use for processing"
    )
    
    include_raw_text = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Include extracted raw text in response (for debugging)"
    )


class ResumeDataSerializer(serializers.Serializer):
    """
    Serializer for structured resume response data
    """
    # Personal Information
    name = serializers.CharField(max_length=200, allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    phone = serializers.CharField(max_length=50, allow_null=True, required=False)
    location = serializers.CharField(max_length=200, allow_null=True, required=False)
    linkedin_url = serializers.URLField(allow_null=True, required=False)
    website_url = serializers.URLField(allow_null=True, required=False)
    
    # Professional Summary
    summary = serializers.CharField(allow_null=True, required=False)
    
    # Skills (both flat list and categorized)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        allow_empty=True,
        required=False,
        help_text="Flat list of all identified skills"
    )
    
    categorized_skills = serializers.ListField(
        child=SkillCategorySerializer(),
        allow_empty=True,
        required=False,
        help_text="Skills organized by category (technical, soft skills, etc.)"
    )
    
    # Experience and Education
    experience = serializers.ListField(
        child=ExperienceSerializer(),
        allow_empty=True,
        required=False
    )
    
    education = serializers.ListField(
        child=EducationSerializer(),
        allow_empty=True,
        required=False
    )
    
    # Languages
    languages = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=True,
        required=False
    )
    
    # Certifications
    certifications = serializers.ListField(
        child=serializers.CharField(max_length=200),
        allow_empty=True,
        required=False
    )
    
    # Processing Metadata
    processing_backend_used = serializers.CharField(
        max_length=20,
        help_text="Backend that was actually used for processing"
    )
    
    confidence_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        allow_null=True,
        required=False,
        help_text="Overall confidence score for extracted data (0.0 to 1.0)"
    )
    
    processing_time_seconds = serializers.FloatField(
        min_value=0.0,
        required=False,
        help_text="Time taken to process the resume"
    )
    
    # Optional raw text (for debugging)
    raw_text = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Raw extracted text from PDF (only if requested)"
    )
    
    # Warnings and errors
    warnings = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
        help_text="Non-fatal warnings during processing"
    )


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error responses
    """
    error = serializers.DictField(
        child=serializers.CharField(),
        help_text="Error details including code, message, and additional info"
    )


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check responses
    """
    status = serializers.CharField(help_text="Overall system status")
    backends = serializers.DictField(
        child=serializers.DictField(),
        help_text="Status of each AI backend"
    )
    configuration = serializers.DictField(
        child=serializers.CharField(),
        help_text="Current system configuration"
    )