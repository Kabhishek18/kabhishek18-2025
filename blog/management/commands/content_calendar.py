from django.core.management.base import BaseCommand
from blog.models import Post, Category, Tag
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

class Command(BaseCommand):
    help = 'Manage content calendar and publishing schedule'

    def add_arguments(self, parser):
        parser.add_argument('--view', action='store_true', help='View content calendar')
        parser.add_argument('--plan', action='store_true', help='Plan content for next month')
        parser.add_argument('--status', action='store_true', help='Show publishing status')
        parser.add_argument('--month', type=int, help='Month to view (1-12)')
        parser.add_argument('--year', type=int, help='Year to view')

    def handle(self, *args, **options):
        if options.get('view'):
            month = options.get('month', timezone.now().month)
            year = options.get('year', timezone.now().year)
            self.view_calendar(month, year)
        
        if options.get('plan'):
            self.plan_monthly_content()
        
        if options.get('status'):
            self.show_publishing_status()
        
        if not any([options.get('view'), options.get('plan'), options.get('status')]):
            self.show_publishing_status()

    def view_calendar(self, month, year):
        """Display content calendar for specified month"""
        self.stdout.write(f"\n📅 Content Calendar - {calendar.month_name[month]} {year}")
        self.stdout.write("=" * 60)
        
        # Get posts for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        posts = Post.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).order_by('created_at')
        
        # Group posts by date
        posts_by_date = {}
        for post in posts:
            date_key = post.created_at.date()
            if date_key not in posts_by_date:
                posts_by_date[date_key] = []
            posts_by_date[date_key].append(post)
        
        # Display calendar
        cal = calendar.monthcalendar(year, month)
        
        # Header
        self.stdout.write("\nMon Tue Wed Thu Fri Sat Sun")
        self.stdout.write("-" * 28)
        
        for week in cal:
            week_str = ""
            for day in week:
                if day == 0:
                    week_str += "    "
                else:
                    date_obj = datetime(year, month, day).date()
                    if date_obj in posts_by_date:
                        week_str += f"{day:2d}* "  # Mark days with posts
                    else:
                        week_str += f"{day:2d}  "
            self.stdout.write(week_str)
        
        # Legend
        self.stdout.write("\n* = Content published")
        
        # Detailed post list
        if posts_by_date:
            self.stdout.write(f"\n📝 Published Content ({len(posts)} posts):")
            self.stdout.write("-" * 40)
            
            for date, date_posts in sorted(posts_by_date.items()):
                self.stdout.write(f"\n{date.strftime('%B %d, %Y')}:")
                for post in date_posts:
                    status_icon = "✅" if post.status == 'published' else "📝"
                    self.stdout.write(f"  {status_icon} {post.title}")
                    self.stdout.write(f"     Categories: {', '.join([c.name for c in post.categories.all()])}")
        
        # Publishing frequency analysis
        self.stdout.write(f"\n📊 Publishing Statistics:")
        self.stdout.write(f"  Total posts: {len(posts)}")
        self.stdout.write(f"  Published: {posts.filter(status='published').count()}")
        self.stdout.write(f"  Drafts: {posts.filter(status='draft').count()}")
        
        # Calculate weekly average
        weeks_in_month = len(cal)
        avg_per_week = len(posts) / weeks_in_month if weeks_in_month > 0 else 0
        self.stdout.write(f"  Average per week: {avg_per_week:.1f}")
        
        if avg_per_week < 2:
            self.stdout.write("  ⚠️  Below target of 2-3 posts per week")
        elif avg_per_week > 3:
            self.stdout.write("  🎉 Above target publishing rate!")
        else:
            self.stdout.write("  ✅ Meeting target of 2-3 posts per week")

    def plan_monthly_content(self):
        """Plan content for the next month"""
        self.stdout.write("📋 Planning content for next month...")
        
        next_month = timezone.now().replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        self.stdout.write(f"\n🎯 Content Plan for {next_month.strftime('%B %Y')}")
        self.stdout.write("=" * 50)
        
        # Content themes for different weeks
        weekly_themes = [
            {
                'week': 1,
                'theme': 'Django & Python Fundamentals',
                'topics': [
                    'Django Model Optimization Techniques',
                    'Python Design Patterns for Web Development',
                    'Django Testing Best Practices'
                ]
            },
            {
                'week': 2,
                'theme': 'Frontend & JavaScript',
                'topics': [
                    'Modern JavaScript ES2024 Features',
                    'CSS Grid Advanced Layouts',
                    'Frontend Performance Optimization'
                ]
            },
            {
                'week': 3,
                'theme': 'Database & Performance',
                'topics': [
                    'PostgreSQL Advanced Queries',
                    'Database Connection Pooling',
                    'Caching Strategies for Web Apps'
                ]
            },
            {
                'week': 4,
                'theme': 'DevOps & Deployment',
                'topics': [
                    'Docker Multi-stage Builds',
                    'CI/CD Pipeline Best Practices',
                    'Monitoring and Logging Strategies'
                ]
            }
        ]
        
        for week_plan in weekly_themes:
            self.stdout.write(f"\n📅 Week {week_plan['week']}: {week_plan['theme']}")
            self.stdout.write("-" * 30)
            
            for i, topic in enumerate(week_plan['topics'], 1):
                # Calculate publishing dates (Mon, Wed, Fri)
                week_start = next_month + timedelta(weeks=week_plan['week']-1)
                monday = week_start - timedelta(days=week_start.weekday())
                
                if i == 1:
                    pub_date = monday  # Monday
                elif i == 2:
                    pub_date = monday + timedelta(days=2)  # Wednesday
                else:
                    pub_date = monday + timedelta(days=4)  # Friday
                
                self.stdout.write(f"  {pub_date.strftime('%m/%d')}: {topic}")
        
        # Content type distribution
        self.stdout.write(f"\n📊 Recommended Content Mix:")
        self.stdout.write("  • 40% Technical Tutorials")
        self.stdout.write("  • 30% Best Practices & Guides")
        self.stdout.write("  • 20% Comparison Articles")
        self.stdout.write("  • 10% Case Studies")
        
        # SEO keyword suggestions
        self.stdout.write(f"\n🔍 SEO Focus Keywords for {next_month.strftime('%B')}:")
        monthly_keywords = [
            "Django optimization",
            "Python web development",
            "JavaScript performance",
            "Database design patterns",
            "Web application security",
            "API development best practices",
            "DevOps automation",
            "Full-stack development"
        ]
        
        for keyword in monthly_keywords:
            self.stdout.write(f"  • {keyword}")

    def show_publishing_status(self):
        """Show current publishing status and recommendations"""
        self.stdout.write("\n📈 Publishing Status Dashboard")
        self.stdout.write("=" * 40)
        
        # Current month stats
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        current_month_posts = Post.objects.filter(
            created_at__gte=month_start,
            status='published'
        )
        
        # This week stats
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        this_week_posts = Post.objects.filter(
            created_at__gte=week_start,
            status='published'
        )
        
        # Draft posts
        draft_posts = Post.objects.filter(status='draft')
        
        self.stdout.write(f"\n📊 Current Statistics:")
        self.stdout.write(f"  This month: {current_month_posts.count()} posts published")
        self.stdout.write(f"  This week: {this_week_posts.count()} posts published")
        self.stdout.write(f"  Draft posts: {draft_posts.count()} ready for editing")
        
        # Calculate days remaining in month
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        
        days_remaining = (next_month - now).days
        weeks_remaining = days_remaining / 7
        
        # Publishing pace analysis
        target_monthly = 12  # 3 posts per week * 4 weeks
        current_pace = current_month_posts.count()
        projected_monthly = current_pace + (this_week_posts.count() * weeks_remaining)
        
        self.stdout.write(f"\n🎯 Publishing Pace Analysis:")
        self.stdout.write(f"  Target for month: {target_monthly} posts")
        self.stdout.write(f"  Current progress: {current_pace} posts")
        self.stdout.write(f"  Projected total: {projected_monthly:.0f} posts")
        
        if projected_monthly >= target_monthly:
            self.stdout.write("  ✅ On track to meet publishing goals!")
        else:
            needed = target_monthly - current_pace
            self.stdout.write(f"  ⚠️  Need {needed} more posts to meet monthly target")
        
        # Content category analysis
        self.stdout.write(f"\n📂 Content Category Distribution:")
        categories = Category.objects.annotate(
            post_count=models.Count('posts', filter=models.Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-post_count')
        
        for category in categories[:5]:
            percentage = (category.post_count / Post.objects.filter(status='published').count()) * 100
            self.stdout.write(f"  {category.name}: {category.post_count} posts ({percentage:.1f}%)")
        
        # Recommendations
        self.stdout.write(f"\n💡 Recommendations:")
        
        if this_week_posts.count() < 2:
            self.stdout.write("  • Publish 1-2 more posts this week to stay on track")
        
        if draft_posts.count() < 5:
            self.stdout.write("  • Create more draft posts to maintain publishing pipeline")
        
        # Check for content gaps
        all_posts = Post.objects.filter(status='published')
        if all_posts.count() > 0:
            avg_length = sum(len(post.content) for post in all_posts) / all_posts.count()
            if avg_length < 3000:
                self.stdout.write("  • Focus on creating longer, more comprehensive content")
        
        # SEO recommendations
        posts_without_excerpts = Post.objects.filter(
            status='published',
            excerpt__isnull=True
        ).count()
        
        if posts_without_excerpts > 0:
            self.stdout.write(f"  • Add meta descriptions to {posts_without_excerpts} posts")
        
        self.stdout.write(f"\n🚀 Next Actions:")
        self.stdout.write("  1. Run: python manage.py content_pipeline --generate --count 5")
        self.stdout.write("  2. Complete 2-3 draft posts this week")
        self.stdout.write("  3. Schedule social media promotion for published posts")
        self.stdout.write("  4. Review and update older posts for SEO")

# Add the missing import
from django.db import models