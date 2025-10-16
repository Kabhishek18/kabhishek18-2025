# Requirements Document

## Introduction

The Resume Parser feature is a Django application that allows users to upload PDF resumes and extract key information such as name, email, skills, and experience using natural language processing. The system will process the resume in real-time and return structured data without storing the uploaded file, ensuring privacy and compliance.

## Requirements

### Requirement 1

**User Story:** As a recruiter, I want to upload a PDF resume, so that I can quickly extract structured information without manual data entry.

#### Acceptance Criteria

1. WHEN a user uploads a PDF file THEN the system SHALL validate that the file is a valid PDF format
2. WHEN a PDF is uploaded THEN the system SHALL extract text content from the PDF
3. WHEN text extraction is complete THEN the system SHALL process the text to identify name, email, skills, and experience
4. WHEN processing is complete THEN the system SHALL return structured JSON data with extracted information
5. WHEN the response is sent THEN the system SHALL immediately delete the uploaded file from temporary storage

### Requirement 2

**User Story:** As a user, I want the system to accurately identify contact information, so that I can quickly reach out to candidates.

#### Acceptance Criteria

1. WHEN processing resume text THEN the system SHALL extract the candidate's full name using NLP techniques
2. WHEN processing resume text THEN the system SHALL identify and validate email addresses using regex patterns
3. WHEN processing resume text THEN the system SHALL extract phone numbers if present
4. WHEN no contact information is found THEN the system SHALL return appropriate null values in the response
5. WHEN multiple email addresses are found THEN the system SHALL return the primary/first email address

### Requirement 3

**User Story:** As a hiring manager, I want to see extracted skills and experience, so that I can quickly assess candidate qualifications.

#### Acceptance Criteria

1. WHEN processing resume text THEN the system SHALL identify technical skills using keyword matching and NLP
2. WHEN processing resume text THEN the system SHALL extract work experience including job titles and companies
3. WHEN processing resume text THEN the system SHALL identify years of experience or employment dates
4. WHEN processing resume text THEN the system SHALL extract education information if present
5. WHEN skills are identified THEN the system SHALL categorize them (e.g., technical, soft skills, languages)

### Requirement 4

**User Story:** As a system administrator, I want the application to handle errors gracefully, so that users receive helpful feedback when issues occur.

#### Acceptance Criteria

1. WHEN an invalid file format is uploaded THEN the system SHALL return a 400 error with descriptive message
2. WHEN PDF text extraction fails THEN the system SHALL return a 422 error indicating processing failure
3. WHEN the uploaded file is corrupted THEN the system SHALL return appropriate error response
4. WHEN file size exceeds limits THEN the system SHALL return a 413 error with size limit information
5. WHEN AI/NLP processing fails THEN the system SHALL return partial results with error indicators

### Requirement 5

**User Story:** As a privacy-conscious user, I want assurance that my resume data is not stored, so that I can trust the system with sensitive information.

#### Acceptance Criteria

1. WHEN a file is uploaded THEN the system SHALL store it only in temporary memory or temp directory
2. WHEN processing is complete THEN the system SHALL immediately delete all temporary files
3. WHEN an error occurs during processing THEN the system SHALL still clean up temporary files
4. WHEN the API response is sent THEN the system SHALL confirm no resume data persists in storage
5. WHEN system logs are created THEN the system SHALL NOT log sensitive resume content

### Requirement 6

**User Story:** As a developer, I want the system to integrate with existing AI models, so that I can leverage Gemini or spaCy for accurate text processing.

#### Acceptance Criteria

1. WHEN configuring the system THEN the system SHALL support both Gemini AI and spaCy as processing backends
2. WHEN using Gemini AI THEN the system SHALL send extracted text to Gemini API for structured extraction
3. WHEN using spaCy THEN the system SHALL use local NLP models for entity recognition
4. WHEN AI processing fails THEN the system SHALL fallback to rule-based extraction methods
5. WHEN processing is complete THEN the system SHALL return consistent JSON structure regardless of backend used