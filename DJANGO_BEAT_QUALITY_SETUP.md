# Django Beat Quality Score Monitoring

Automated daily quality score updates using Django Beat (Celery Beat) for AdSense compliance monitoring.

## 📋 Overview

This system automatically:
- **Updates quality scores daily** at 2:00 AM
- **Generates weekly reports** on Mondays at 6:00 AM
- **Tracks quality trends** over time
- **Alerts on low-quality content**
- **Ensures AdSense compliance**

## 🚀 Quick Setup

### 1. Install Requirements

```bash
pip install celery django-celery-beat redis
```

### 2. Configure Django Settings

Add to your `settings.py`:

```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... your existing apps
    'django_celery_beat',
]

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Import Beat Configuration
from celery_beat_config import (
    CELERY_BEAT_SCHEDULE, 
    CELERY_TIMEZONE,
    CELERY_BEAT_SCHEDULER
)

CELERY_BEAT_SCHEDULE = CELERY_BEAT_SCHEDULE
CELERY_TIMEZONE = 'UTC'  # Change to your timezone
CELERY_BEAT_SCHEDULER = CELERY_BEAT_SCHEDULER
```

### 3. Run Automated Setup

```bash
python setup_django_beat_quality.py
```

This will:
- ✅ Check Celery and Beat installation
- ✅ Run database migrations
- ✅ Create scheduled tasks
- ✅ Test the quality update system

### 4. Start Celery Services

**Option A: Separate Processes (Recommended for Production)**

```bash
# Terminal 1: Celery Worker
celery -A kabhishek18 worker --loglevel=info

# Terminal 2: Celery Beat
celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Option B: Combined Process (Development)**

```bash
celery -A kabhishek18 worker --beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 📊 Scheduled Tasks

### Daily Quality Update (2:00 AM)
- **Task**: `blog.tasks.daily_quality_update`
- **Frequency**: Daily at 2:00 AM
- **Function**: Updates quality scores for up to 50 posts
- **Output**: Quality scores cached for 24 hours

### Weekly Quality Report (Monday 6:00 AM)
- **Task**: `blog.tasks.weekly_quality_report`
- **Frequency**: Weekly on Mondays at 6:00 AM
- **Function**: Comprehensive quality audit and trend analysis
- **Output**: Detailed quality report with recommendations

## 🔧 Manual Testing

### Test Tasks Immediately

```bash
# Test daily quality update
python manage.py trigger_quality_task --task daily

# Test weekly report
python manage.py trigger_quality_task --task weekly

# Test both tasks
python manage.py trigger_quality_task --task both

# Run asynchronously (requires Celery worker running)
python manage.py trigger_quality_task --task daily --async --wait
```

### Run Quality Update Directly

```bash
# Update quality scores for all posts
python manage.py update_quality_scores

# Update with full reporting
python manage.py update_quality_scores --generate-report --alert-low-quality --save-history

# Update only published posts
python manage.py update_quality_scores --only-published --posts-per-run 50
```

## 📈 Monitoring

### Django Admin

1. Go to Django Admin → Periodic Tasks
2. View scheduled tasks:
   - Daily Quality Score Update
   - Weekly Quality Report
3. Check task status, last run time, and enable/disable tasks

### Check Quality Scores

```python
# In Django shell
from blog.management.commands.update_quality_scores import get_post_quality_score, get_site_quality_summary

# Get score for specific post
score = get_post_quality_score(post_id=1)
print(f"Quality Score: {score}")

# Get overall site quality
summary = get_site_quality_summary()
print(f"Average Score: {summary['average_score']}")
print(f"Quality Status: {summary['quality_status']}")
```

### View Task Results

```python
# In Django shell
from django_celery_beat.models import PeriodicTask

# Check task status
daily_task = PeriodicTask.objects.get(name='Daily Quality Score Update')
print(f"Enabled: {daily_task.enabled}")
print(f"Last Run: {daily_task.last_run_at}")
print(f"Total Runs: {daily_task.total_run_count}")
```

## 🎯 What Gets Monitored

### Quality Metrics
- **Content Length**: Word count and character count
- **Readability**: Flesch Reading Ease score
- **Structure**: Headings, paragraphs, lists, code examples
- **SEO**: Title, meta description, keyword optimization
- **Uniqueness**: Content originality and vocabulary diversity
- **AdSense Compliance**: Policy adherence and value assessment

### Quality Thresholds
- **Excellent**: 90+ score
- **Good**: 75-89 score
- **Fair**: 60-74 score
- **Poor**: <60 score (triggers alerts)

### Alerts
- Posts scoring below 75 trigger quality alerts
- Critical alerts for posts below 50
- Recommendations for improvement provided
- Suggestions to use CRAG for regeneration

## 📋 Task Configuration

### Modify Schedule

Edit `celery_beat_config.py` to change schedules:

```python
CELERY_BEAT_SCHEDULE = {
    'daily-quality-update': {
        'task': 'blog.tasks.daily_quality_update',
        'schedule': crontab(hour=2, minute=0),  # Change time here
    },
}
```

Or modify in Django Admin → Periodic Tasks → Edit schedule

### Adjust Processing Limits

The daily task processes 50 posts per run by default. To change:

```python
# In blog/tasks.py, modify the call_command parameters:
call_command(
    'update_quality_scores',
    posts_per_run=100,  # Process more posts
    # ... other options
)
```

## 🔍 Troubleshooting

### Tasks Not Running

1. **Check Celery Worker is Running**:
   ```bash
   celery -A kabhishek18 inspect active
   ```

2. **Check Beat Scheduler is Running**:
   ```bash
   celery -A kabhishek18 inspect scheduled
   ```

3. **Verify Tasks in Database**:
   ```bash
   python manage.py shell
   >>> from django_celery_beat.models import PeriodicTask
   >>> PeriodicTask.objects.filter(enabled=True)
   ```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running, start Redis
redis-server
```

### Task Execution Errors

Check Celery logs for detailed error messages:
```bash
# Worker logs show task execution
celery -A kabhishek18 worker --loglevel=debug

# Beat logs show scheduling
celery -A kabhishek18 beat --loglevel=debug
```

## 📊 Quality Reports

### Daily Report Location
- Cached in Redis for 24 hours
- Accessible via `get_post_quality_score(post_id)`
- Includes detailed metrics and issues

### Weekly Report Location
- Generated as JSON files: `quality_report_YYYYMMDD_HHMMSS.json`
- Contains comprehensive analysis
- Includes trend data and recommendations

### Report Contents
- Total posts processed
- Average quality score
- Score distribution (excellent/good/fair/poor)
- Low-quality post alerts
- Improvement recommendations
- AdSense readiness assessment

## 🎛️ Production Deployment

### Using Supervisor (Recommended)

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery-worker]
command=/path/to/venv/bin/celery -A kabhishek18 worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log

[program:celery-beat]
command=/path/to/venv/bin/celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery-worker celery-beat
```

### Using systemd

Create service files for worker and beat, then:
```bash
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

## 📚 Related Commands

- `python manage.py generate_crag_content` - Generate high-quality content
- `python manage.py upgrade_to_crag` - Audit and upgrade existing content
- `python manage.py test_crag` - Test CRAG system functionality

## 🔗 Integration with CRAG

The quality monitoring system works seamlessly with CRAG:

1. **Quality scores identify** low-quality posts
2. **CRAG regenerates** content to meet standards
3. **Quality monitoring tracks** improvements over time
4. **Automated alerts** trigger when quality drops

This creates a continuous improvement cycle for your content.

## ✅ Success Indicators

Your system is working correctly when:
- ✅ Celery worker and beat are running
- ✅ Tasks appear in Django Admin → Periodic Tasks
- ✅ Quality scores are cached and accessible
- ✅ Daily updates run at scheduled time
- ✅ Weekly reports are generated
- ✅ Low-quality posts trigger alerts
- ✅ Quality trends are tracked over time

## 📞 Support

If you encounter issues:
1. Check Celery worker and beat logs
2. Verify Redis connection
3. Test tasks manually with `trigger_quality_task`
4. Review Django Admin periodic tasks
5. Check quality score cache with `get_post_quality_score()`