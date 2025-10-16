from django.core.management.base import BaseCommand
import os
import json
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Setup automated publishing system with cron jobs'

    def add_arguments(self, parser):
        parser.add_argument('--schedule', choices=['daily', 'weekly', 'custom'], default='weekly',
                          help='Publishing schedule')
        parser.add_argument('--quality', choices=['standard', 'premium', 'expert'], default='premium',
                          help='Default content quality')
        parser.add_argument('--posts-per-day', type=int, default=1, help='Posts per publishing day')
        parser.add_argument('--show-cron', action='store_true', help='Show cron job examples')

    def handle(self, *args, **options):
        schedule = options['schedule']
        quality = options['quality']
        posts_per_day = options['posts_per_day']
        
        if options['show_cron']:
            self.show_cron_examples()
            return
        
        # Create configuration
        config = self.create_publishing_config(schedule, quality, posts_per_day)
        
        # Save configuration
        self.save_config(config)
        
        # Show setup instructions
        self.show_setup_instructions(config)

    def create_publishing_config(self, schedule, quality, posts_per_day):
        """Create publishing configuration"""
        config = {
            'schedule': schedule,
            'quality': quality,
            'posts_per_day': posts_per_day,
            'created_at': datetime.now().isoformat(),
            'settings': {
                'max_posts_per_day': 3,
                'min_hours_between_posts': 4,
                'auto_feature_posts': True,
                'generate_images': True,
                'publish_immediately': True,
                'backup_drafts': True
            },
            'schedules': {
                'daily': {
                    'description': 'Publish 1 post every day',
                    'cron': '0 9 * * *',  # 9 AM daily
                    'command': 'auto_publish_content --count 1 --quality {quality}'
                },
                'weekly': {
                    'description': 'Publish 2-3 posts per week (Mon, Wed, Fri)',
                    'cron_jobs': [
                        {'cron': '0 9 * * 1', 'command': 'auto_publish_content --count 1 --quality {quality}'},  # Monday
                        {'cron': '0 9 * * 3', 'command': 'auto_publish_content --count 1 --quality {quality}'},  # Wednesday
                        {'cron': '0 9 * * 5', 'command': 'auto_publish_content --count 1 --quality {quality}'}   # Friday
                    ]
                },
                'custom': {
                    'description': 'Custom schedule based on your needs',
                    'note': 'Configure manually based on your requirements'
                }
            }
        }
        
        return config

    def save_config(self, config):
        """Save configuration to file"""
        config_file = 'auto_publishing_config.json'
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.stdout.write(f"✅ Configuration saved to {config_file}")
            
        except Exception as e:
            self.stdout.write(f"❌ Error saving configuration: {str(e)}")

    def show_setup_instructions(self, config):
        """Show setup instructions"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("🚀 AUTOMATED PUBLISHING SETUP COMPLETE")
        self.stdout.write("="*60)
        
        self.stdout.write(f"\n📋 Configuration:")
        self.stdout.write(f"   Schedule: {config['schedule']}")
        self.stdout.write(f"   Quality: {config['quality']}")
        self.stdout.write(f"   Posts per day: {config['posts_per_day']}")
        
        self.stdout.write(f"\n⚙️ Setup Instructions:")
        
        if config['schedule'] == 'daily':
            self.show_daily_setup(config)
        elif config['schedule'] == 'weekly':
            self.show_weekly_setup(config)
        else:
            self.show_custom_setup(config)
        
        self.stdout.write(f"\n🔧 Manual Commands:")
        self.stdout.write(f"   Generate 1 post now:")
        self.stdout.write(f"   python manage.py auto_publish_content --count 1 --quality {config['quality']}")
        
        self.stdout.write(f"\n   Generate 3 posts (dry run):")
        self.stdout.write(f"   python manage.py auto_publish_content --count 3 --quality {config['quality']} --dry-run")
        
        self.stdout.write(f"\n   Force generation (ignore limits):")
        self.stdout.write(f"   python manage.py auto_publish_content --count 1 --force")
        
        self.stdout.write(f"\n📊 Monitoring:")
        self.stdout.write(f"   Check publishing status:")
        self.stdout.write(f"   python manage.py content_calendar --status")
        
        self.stdout.write(f"\n   View content calendar:")
        self.stdout.write(f"   python manage.py content_calendar --view")

    def show_daily_setup(self, config):
        """Show daily publishing setup"""
        self.stdout.write(f"\n📅 DAILY PUBLISHING SETUP")
        self.stdout.write(f"   • 1 post will be published every day at 9:00 AM")
        self.stdout.write(f"   • Quality level: {config['quality']}")
        
        self.stdout.write(f"\n🔧 Cron Job Setup:")
        self.stdout.write(f"   Add this line to your crontab (crontab -e):")
        self.stdout.write(f"   0 9 * * * cd /path/to/your/project && python manage.py auto_publish_content --count 1 --quality {config['quality']}")
        
        self.stdout.write(f"\n   Or use this full command with logging:")
        cron_command = f"0 9 * * * cd /path/to/your/project && /path/to/python manage.py auto_publish_content --count 1 --quality {config['quality']} >> /var/log/auto_publish.log 2>&1"
        self.stdout.write(f"   {cron_command}")

    def show_weekly_setup(self, config):
        """Show weekly publishing setup"""
        self.stdout.write(f"\n📅 WEEKLY PUBLISHING SETUP (2-3 posts per week)")
        self.stdout.write(f"   • Monday: 1 post at 9:00 AM")
        self.stdout.write(f"   • Wednesday: 1 post at 9:00 AM") 
        self.stdout.write(f"   • Friday: 1 post at 9:00 AM")
        self.stdout.write(f"   • Quality level: {config['quality']}")
        
        self.stdout.write(f"\n🔧 Cron Job Setup:")
        self.stdout.write(f"   Add these lines to your crontab (crontab -e):")
        
        project_path = "/path/to/your/project"
        python_path = "/path/to/python"
        log_file = "/var/log/auto_publish.log"
        
        cron_jobs = [
            f"0 9 * * 1 cd {project_path} && {python_path} manage.py auto_publish_content --count 1 --quality {config['quality']} >> {log_file} 2>&1",
            f"0 9 * * 3 cd {project_path} && {python_path} manage.py auto_publish_content --count 1 --quality {config['quality']} >> {log_file} 2>&1", 
            f"0 9 * * 5 cd {project_path} && {python_path} manage.py auto_publish_content --count 1 --quality {config['quality']} >> {log_file} 2>&1"
        ]
        
        for job in cron_jobs:
            self.stdout.write(f"   {job}")

    def show_custom_setup(self, config):
        """Show custom setup options"""
        self.stdout.write(f"\n📅 CUSTOM PUBLISHING SETUP")
        self.stdout.write(f"   Configure your own schedule using cron syntax")
        self.stdout.write(f"   Quality level: {config['quality']}")
        
        self.stdout.write(f"\n🔧 Example Cron Patterns:")
        examples = [
            ("Every day at 10 AM", "0 10 * * *"),
            ("Twice daily (9 AM, 6 PM)", "0 9,18 * * *"),
            ("Weekdays only at 9 AM", "0 9 * * 1-5"),
            ("Every 6 hours", "0 */6 * * *"),
            ("Sundays at 8 AM", "0 8 * * 0")
        ]
        
        for desc, cron in examples:
            self.stdout.write(f"   {desc}: {cron}")

    def show_cron_examples(self):
        """Show comprehensive cron examples"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📅 CRON JOB EXAMPLES FOR AUTO PUBLISHING")
        self.stdout.write("="*60)
        
        self.stdout.write(f"\n🔧 Basic Setup:")
        self.stdout.write(f"   1. Edit crontab: crontab -e")
        self.stdout.write(f"   2. Add your chosen schedule")
        self.stdout.write(f"   3. Save and exit")
        
        self.stdout.write(f"\n📋 Publishing Schedules:")
        
        schedules = [
            {
                'name': 'Conservative (2 posts/week)',
                'description': 'Tuesday and Friday at 9 AM',
                'cron': [
                    '0 9 * * 2 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium',
                    '0 9 * * 5 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium'
                ]
            },
            {
                'name': 'Balanced (3 posts/week)',
                'description': 'Monday, Wednesday, Friday at 9 AM',
                'cron': [
                    '0 9 * * 1 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium',
                    '0 9 * * 3 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium',
                    '0 9 * * 5 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium'
                ]
            },
            {
                'name': 'Aggressive (5 posts/week)',
                'description': 'Weekdays at 9 AM',
                'cron': [
                    '0 9 * * 1-5 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium'
                ]
            },
            {
                'name': 'Daily Publishing',
                'description': 'Every day at 9 AM',
                'cron': [
                    '0 9 * * * cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium'
                ]
            }
        ]
        
        for schedule in schedules:
            self.stdout.write(f"\n📌 {schedule['name']}")
            self.stdout.write(f"   {schedule['description']}")
            for cron_job in schedule['cron']:
                self.stdout.write(f"   {cron_job}")
        
        self.stdout.write(f"\n🔍 Advanced Options:")
        
        advanced_examples = [
            {
                'name': 'Different Quality Levels',
                'description': 'High quality on Monday, standard on Friday',
                'cron': [
                    '0 9 * * 1 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality expert',
                    '0 9 * * 5 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality standard'
                ]
            },
            {
                'name': 'Multiple Posts Per Day',
                'description': 'Morning and evening posts',
                'cron': [
                    '0 9 * * 1,3,5 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality premium',
                    '0 18 * * 2,4 cd /path/to/project && python manage.py auto_publish_content --count 1 --quality standard'
                ]
            },
            {
                'name': 'With Logging and Error Handling',
                'description': 'Full production setup with logging',
                'cron': [
                    '0 9 * * 1,3,5 cd /path/to/project && /usr/bin/python3 manage.py auto_publish_content --count 1 --quality premium >> /var/log/auto_publish.log 2>&1'
                ]
            }
        ]
        
        for example in advanced_examples:
            self.stdout.write(f"\n📌 {example['name']}")
            self.stdout.write(f"   {example['description']}")
            for cron_job in example['cron']:
                self.stdout.write(f"   {cron_job}")
        
        self.stdout.write(f"\n⚠️ Important Notes:")
        self.stdout.write(f"   • Replace '/path/to/project' with your actual project path")
        self.stdout.write(f"   • Replace '/usr/bin/python3' with your Python path")
        self.stdout.write(f"   • Ensure GEMINI_API_KEY is set in your environment")
        self.stdout.write(f"   • Test commands manually before adding to cron")
        self.stdout.write(f"   • Monitor logs for any issues")
        
        self.stdout.write(f"\n🧪 Testing Commands:")
        self.stdout.write(f"   Test generation (dry run):")
        self.stdout.write(f"   python manage.py auto_publish_content --count 1 --dry-run")
        
        self.stdout.write(f"\n   Generate and publish immediately:")
        self.stdout.write(f"   python manage.py auto_publish_content --count 1 --quality premium")
        
        self.stdout.write(f"\n   Check if cron is working:")
        self.stdout.write(f"   tail -f /var/log/auto_publish.log")

    def create_sample_env_file(self):
        """Create sample environment file"""
        env_content = """
# Auto Publishing Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration (if needed)
DATABASE_URL=your_database_url

# Optional: Email notifications
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Optional: Slack notifications
SLACK_WEBHOOK_URL=your_slack_webhook_url
        """
        
        try:
            with open('.env.auto_publish', 'w') as f:
                f.write(env_content.strip())
            
            self.stdout.write(f"✅ Sample environment file created: .env.auto_publish")
            
        except Exception as e:
            self.stdout.write(f"❌ Error creating env file: {str(e)}")