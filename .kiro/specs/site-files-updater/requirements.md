# Requirements Document

## Introduction

This feature will create an automated system to update the site's metadata files (Sitemap.xml, robots.txt, security.txt) with the latest available URLs from the website. Additionally, it will add a new LLMs.txt file to provide guidance for large language models interacting with the site. The system will run as a scheduled cron job to ensure these files are always up-to-date.

## Requirements

### Requirement 1: Sitemap.xml Generator

**User Story:** As a site administrator, I want the Sitemap.xml to be automatically updated with all available URLs, so that search engines can properly index the site.

#### Acceptance Criteria

1. WHEN the cron job runs THEN the system SHALL scan all available URLs from the Django URL patterns
2. WHEN generating the sitemap THEN the system SHALL include all public-facing URLs
3. WHEN generating the sitemap THEN the system SHALL exclude admin URLs and other non-public URLs
4. WHEN generating the sitemap THEN the system SHALL include dynamic URLs from database content (e.g., blog posts)
5. WHEN generating the sitemap THEN the system SHALL maintain the proper XML format with lastmod, changefreq, and priority attributes
6. WHEN the sitemap is generated THEN the system SHALL write it to the static/Sitemap.xml file
7. IF the sitemap generation fails THEN the system SHALL log the error and maintain the previous sitemap file

### Requirement 2: robots.txt Updater

**User Story:** As a site administrator, I want the robots.txt file to be automatically updated with the latest sitemap URL and crawling rules, so that search engines know what to index.

#### Acceptance Criteria

1. WHEN the cron job runs THEN the system SHALL update the robots.txt file with the current sitemap URL
2. WHEN updating robots.txt THEN the system SHALL maintain existing user-agent rules and disallow directives
3. WHEN updating robots.txt THEN the system SHALL ensure the sitemap URL is correct and points to the absolute URL
4. IF the robots.txt update fails THEN the system SHALL log the error and maintain the previous robots.txt file

### Requirement 3: security.txt Updater

**User Story:** As a site administrator, I want the security.txt file to be automatically updated with the latest contact information and canonical URL, so that security researchers can properly report vulnerabilities.

#### Acceptance Criteria

1. WHEN the cron job runs THEN the system SHALL update the security.txt file with the current canonical URL
2. WHEN updating security.txt THEN the system SHALL maintain existing contact information and other directives
3. WHEN updating security.txt THEN the system SHALL ensure the canonical URL is correct and points to the absolute URL
4. IF the security.txt update fails THEN the system SHALL log the error and maintain the previous security.txt file

### Requirement 4: LLMs.txt Creator

**User Story:** As a site administrator, I want to add an LLMs.txt file to provide guidance for large language models interacting with the site, so that AI systems can better understand the site's structure and content.

#### Acceptance Criteria

1. WHEN the cron job runs THEN the system SHALL create or update the LLMs.txt file
2. WHEN creating LLMs.txt THEN the system SHALL include information about the site's structure, content types, and navigation
3. WHEN creating LLMs.txt THEN the system SHALL include information about acceptable AI interactions with the site
4. WHEN creating LLMs.txt THEN the system SHALL include information about the site's API endpoints if they exist
5. WHEN creating LLMs.txt THEN the system SHALL include information about the site's content licensing and usage policies
6. IF the LLMs.txt creation fails THEN the system SHALL log the error

### Requirement 5: Scheduled Execution

**User Story:** As a site administrator, I want these file updates to run automatically on a schedule, so that I don't have to manually trigger them.

#### Acceptance Criteria

1. WHEN the system is deployed THEN it SHALL create a scheduled task using Django's Celery Beat
2. WHEN configuring the schedule THEN the system SHALL set a reasonable default frequency (e.g., daily)
3. WHEN the scheduled task runs THEN the system SHALL execute all file update operations in sequence
4. IF any update operation fails THEN the system SHALL continue with the remaining operations
5. WHEN the scheduled task completes THEN the system SHALL log the results of all operations

### Requirement 6: Manual Trigger

**User Story:** As a site administrator, I want to be able to manually trigger the file updates, so that I can refresh them immediately after making site changes.

#### Acceptance Criteria

1. WHEN a management command is executed THEN the system SHALL run all file update operations
2. WHEN the management command is executed with specific flags THEN the system SHALL run only the specified update operations
3. WHEN the management command completes THEN the system SHALL provide feedback on the success or failure of each operation