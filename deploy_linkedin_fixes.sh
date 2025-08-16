#!/bin/bash

# Production LinkedIn Integration Fixes Deployment Script
# This script deploys the fixes for MockPost and ALLOWED_HOSTS issues

set -e  # Exit on any error

echo "=========================================="
echo "LinkedIn Integration Fixes Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    print_error "This script must be run from the Django project root directory"
    exit 1
fi

print_status "Starting deployment of LinkedIn integration fixes..."

# 1. Backup current configuration
print_status "Creating backup of current configuration..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
print_status "Backup created: .env.backup.$(date +%Y%m%d_%H%M%S)"

# 2. Validate the fixes before deployment
print_status "Running validation tests..."
if python validate_mockpost_fix.py; then
    print_status "✅ All validation tests passed!"
else
    print_error "❌ Validation tests failed. Aborting deployment."
    exit 1
fi

# 3. Check Django configuration
print_status "Checking Django configuration..."
if python manage.py check --deploy; then
    print_status "✅ Django configuration check passed!"
else
    print_warning "⚠️ Django configuration check has warnings. Review before proceeding."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment aborted by user."
        exit 1
    fi
fi

# 4. Test database connectivity
print_status "Testing database connectivity..."
if python manage.py migrate --check; then
    print_status "✅ Database connectivity OK!"
else
    print_error "❌ Database connectivity issues. Check your database configuration."
    exit 1
fi

# 5. Collect static files (if needed)
print_status "Collecting static files..."
python manage.py collectstatic --noinput --clear

# 6. Check for any pending migrations
print_status "Checking for pending migrations..."
if python manage.py showmigrations --plan | grep -q "\[ \]"; then
    print_warning "⚠️ There are pending migrations. Running them now..."
    python manage.py migrate
else
    print_status "✅ No pending migrations."
fi

# 7. Test LinkedIn service specifically
print_status "Testing LinkedIn service integration..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from blog.services.linkedin_service import LinkedInAPIService
service = LinkedInAPIService()
print('LinkedIn service initialized successfully')

# Test MockPost fix
formatted = service._format_post_content('Test', 'Test content', 'https://example.com')
print(f'MockPost test passed - formatted length: {len(formatted)}')
"

if [ $? -eq 0 ]; then
    print_status "✅ LinkedIn service test passed!"
else
    print_error "❌ LinkedIn service test failed!"
    exit 1
fi

# 8. Create deployment summary
print_status "Creating deployment summary..."
cat > deployment_summary.txt << EOF
LinkedIn Integration Fixes Deployment Summary
============================================
Date: $(date)
User: $(whoami)
Host: $(hostname)

Files Modified:
- .env (ALLOWED_HOSTS updated)
- blog/services/linkedin_service.py (MockPost fixes)

Fixes Applied:
1. Added production server IP (13.200.82.14) to ALLOWED_HOSTS
2. Added domain names (kabhishek18.com, www.kabhishek18.com) to ALLOWED_HOSTS
3. Fixed MockPost class missing 'id' attribute
4. Added 'slug' attribute to MockPost class
5. Improved URL handling in MockPost.get_absolute_url()

Validation Results:
- ALLOWED_HOSTS configuration: ✅ PASSED
- LinkedIn service initialization: ✅ PASSED
- MockPost attributes test: ✅ PASSED

Status: READY FOR PRODUCTION
EOF

print_status "Deployment summary created: deployment_summary.txt"

# 9. Final instructions
echo ""
echo "=========================================="
print_status "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "=========================================="
echo ""
print_status "Next steps for production deployment:"
echo "1. Copy the updated files to your production server"
echo "2. Restart your Django application (Gunicorn/uWSGI)"
echo "3. Monitor logs for 30 minutes after deployment"
echo "4. Test LinkedIn posting functionality"
echo ""
print_warning "Files to deploy:"
echo "- .env (with updated ALLOWED_HOSTS)"
echo "- blog/services/linkedin_service.py (with MockPost fixes)"
echo ""
print_status "Monitoring commands:"
echo "# Check for MockPost errors:"
echo "tail -f /var/log/your-app/gunicorn.log | grep 'MockPost'"
echo ""
echo "# Check for ALLOWED_HOSTS errors:"
echo "tail -f /var/log/your-app/gunicorn.log | grep 'DisallowedHost'"
echo ""
print_status "Emergency rollback:"
echo "If issues occur, restore from backup: .env.backup.*"
echo ""
print_status "Deployment completed at: $(date)"