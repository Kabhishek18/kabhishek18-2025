# Django Blog Platform

A comprehensive Django-based blog platform with advanced features including AI content generation, LinkedIn integration, multimedia support, and automated site management.

## Features

- **AI-Powered Content Generation** - Generate blog posts using Google Gemini AI
- **LinkedIn Integration** - Automatic posting to LinkedIn with image support
- **Multimedia Management** - Image processing and gallery features
- **SEO Optimization** - Schema markup, sitemap generation, and meta tags
- **Newsletter System** - Automated newsletter sending
- **API System** - RESTful API with authentication
- **Admin Dashboard** - Enhanced admin interface with Unfold theme
- **Content Discovery** - Featured posts and content recommendations
- **Performance Monitoring** - Health dashboard and metrics tracking

## Prerequisites

- Python 3.8+
- MySQL 5.7+
- Redis 6.0+
- Node.js (for frontend assets)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd django-blog-platform
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
SECRET_KEY='your-secret-key-here'
DEBUG=True
ALLOWED_HOSTS="127.0.0.1,localhost,your-domain.com"
SITE_URL=https://your-domain.com

# Database Configuration
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI Content Generation
GEMINI_API_KEY="your-gemini-api-key"

# LinkedIn Integration
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/admin/linkedin/callback/
LINKEDIN_ENCRYPTION_KEY=your_encryption_key
```

### 5. Database Setup

```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE your_database_name;
exit

# Run migrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Collect Static Files

```bash
python manage.py collectstatic
```

## Running the Application

### Development Server

```bash
python manage.py runserver
```

### With Celery (for background tasks)

Terminal 1 - Django server:
```bash
python manage.py runserver
```

Terminal 2 - Celery worker:
```bash
celery -A kabhishek18 worker --loglevel=info
```

Terminal 3 - Celery beat (for scheduled tasks):
```bash
celery -A kabhishek18 beat --loglevel=info
```

## Management Commands

### Blog Content Management

#### AI Content Generation
```bash
# Generate AI-powered blog posts
python manage.py aicontent

# Options:
python manage.py aicontent --count 5  # Generate 5 posts
python manage.py aicontent --category "Technology"  # Specific category
```

#### Content Discovery
```bash
# Manage featured posts and content discovery
python manage.py manage_content_discovery

# Clear content cache
python manage.py manage_content_discovery --clear-cache

# Update featured posts
python manage.py manage_content_discovery --update-featured
```

### Site Files Management

#### Update Site Metadata Files
```bash
# Update sitemap, robots.txt, security.txt, and LLMs.txt
python manage.py update_site_files

# Generate only sitemap
python manage.py generate_sitemap
```

### LinkedIn Integration

#### Setup LinkedIn Integration
```bash
# Initial LinkedIn setup with guided token creation
python manage.py linkedin_setup
```

#### LinkedIn Operations
```bash
# Manual LinkedIn operations
python manage.py linkedin_operations

# Post specific content to LinkedIn
python manage.py linkedin_operations --post --post-id 123

# Test LinkedIn connection
python manage.py linkedin_operations --test

# Bulk operations
python manage.py linkedin_operations --bulk-post
```

#### LinkedIn Credentials Management
```bash
# Manage LinkedIn API credentials
python manage.py linkedin_credentials

# Fix credential decryption issues
python manage.py fix_linkedin_credentials
```

#### LinkedIn Monitoring & Metrics
```bash
# Display LinkedIn integration metrics
python manage.py linkedin_metrics

# Generate comprehensive metrics report
python manage.py linkedin_metrics_report

# Set up periodic LinkedIn image monitoring
python manage.py setup_linkedin_image_monitoring
```

#### LinkedIn Image Management
```bash
# Validate social sharing images
python manage.py validate_social_images

# Troubleshoot LinkedIn image processing
python manage.py linkedin_image_troubleshoot

# Optimize LinkedIn image performance
python manage.py linkedin_image_performance_optimization

# Demonstrate error handling
python manage.py linkedin_image_error_demo
```

### Newsletter Management

```bash
# Send newsletters with scheduling and batch processing
python manage.py send_newsletter

# Send to specific subscribers
python manage.py send_newsletter --subscribers "email1@example.com,email2@example.com"

# Schedule newsletter
python manage.py send_newsletter --schedule "2024-01-01 10:00"
```

### API Management

#### API Client Management
```bash
# Create new API client with optional API key generation
python manage.py create_api_client

# Create with specific name
python manage.py create_api_client --name "Mobile App Client"
```

#### API Statistics
```bash
# Display API usage statistics
python manage.py api_stats

# Detailed statistics
python manage.py api_stats --detailed
```

#### API Key Cleanup
```bash
# Clean up expired API keys
python manage.py cleanup_expired_keys
```

### Database & Performance

#### Database Optimization
```bash
# Optimize database performance for blog engagement features
python manage.py optimize_database
```

#### Data Migration
```bash
# Migrate existing blog data to support new engagement features
python manage.py migrate_blog_data
```

#### Cleanup Operations
```bash
# Clean up expired confirmation tokens and engagement data
python manage.py cleanup_expired_subscriptions

# Perform security cleanup and maintenance
python manage.py security_cleanup
```

### Backup & Recovery

```bash
# Backup blog engagement data
python manage.py backup_engagement_data

# Restore from backup
python manage.py backup_engagement_data --restore backup_file.json
```

### Validation & Testing

#### Schema Validation
```bash
# Validate schema markup implementation
python manage.py validate_schemas

# Final schema validation
python manage.py validate_schema_final

# Validate LinkedIn Open Graph tags
python manage.py validate_linkedin_open_graph
```

### Development & Debugging

#### Project Setup
```bash
# Automated project setup and management
python manage.py projectsetup
```

#### Screenshots
```bash
# Take screenshots of key website pages
python manage.py screenshot

# Screenshot specific pages
python manage.py screenshot --pages "home,blog,about"
```

#### URL Debugging
```bash
# Debug URL patterns and page routing
python manage.py debug_urls
```

#### Sample Data Creation
```bash
# Create sample media items for testing
python manage.py create_sample_media
```

## API Documentation

The API documentation is available at:
- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`

### API Endpoints

- **Blog Posts**: `/api/posts/`
- **Categories**: `/api/categories/`
- **Authors**: `/api/authors/`
- **Authentication**: `/api/auth/`
- **User Management**: `/api/users/`

## Admin Interface

Access the admin interface at `http://localhost:8000/admin/`

### Key Admin Features

- **Enhanced UI** with Unfold theme
- **Blog Management** - Posts, categories, authors
- **Media Management** - Images, galleries
- **LinkedIn Integration** - Configuration and monitoring
- **API Management** - Clients, keys, usage statistics
- **Newsletter Management** - Subscribers, campaigns
- **System Health** - Performance monitoring

## Configuration

### LinkedIn Integration Setup

1. Create LinkedIn App at [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Configure OAuth redirect URI: `http://your-domain.com/admin/linkedin/callback/`
3. Add credentials to `.env` file
4. Run setup command: `python manage.py linkedin_setup`

### AI Content Generation Setup

1. Get Google Gemini API key from [Google AI Studio](https://makersuite.google.com/)
2. Add `GEMINI_API_KEY` to `.env` file
3. Configure content generation settings in admin panel

### Email Configuration

Add email settings to `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-host'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
```

## Deployment

### Production Checklist

1. Set `DEBUG=False` in `.env`
2. Configure proper `ALLOWED_HOSTS`
3. Set up SSL certificate
4. Configure production database
5. Set up Redis for caching and Celery
6. Configure web server (Nginx/Apache)
7. Set up process manager (Gunicorn/uWSGI)
8. Configure Celery workers and beat scheduler

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations in container
docker-compose exec web python manage.py migrate

# Create superuser in container
docker-compose exec web python manage.py createsuperuser
```

## Monitoring & Maintenance

### Health Dashboard

Access system health at `http://localhost:8000/health/`

### Regular Maintenance Tasks

```bash
# Daily maintenance
python manage.py cleanup_expired_subscriptions
python manage.py cleanup_expired_keys
python manage.py optimize_database

# Weekly maintenance
python manage.py backup_engagement_data
python manage.py linkedin_metrics_report

# Monthly maintenance
python manage.py security_cleanup
python manage.py validate_schemas
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check MySQL service is running
   - Verify database credentials in `.env`

2. **Redis Connection Error**
   - Ensure Redis server is running
   - Check Redis URL in `.env`

3. **LinkedIn Integration Issues**
   - Run `python manage.py linkedin_credentials` to check setup
   - Use `python manage.py fix_linkedin_credentials` for decryption issues

4. **AI Content Generation Fails**
   - Verify Gemini API key is valid
   - Check API quota limits

### Logs

- Django logs: Check `django_debug.log`
- Celery logs: Monitor worker and beat processes
- LinkedIn integration: Use monitoring commands for detailed logs

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the admin health dashboard for system status
- Review logs for detailed error information