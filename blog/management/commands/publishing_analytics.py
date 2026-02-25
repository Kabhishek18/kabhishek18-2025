from django.core.management.base import BaseCommand
from blog.models import Post, Category, Tag
from django.utils import timezone
from datetime import datetime, timedelta
import json
import os

class Command(BaseCommand):
    help = 'Analytics and monitoring for automated publishing system'

    def add_arguments(self, parser):
        parser.add_argument('--report', choices=['daily', 'weekly', 'monthly'], default='weekly',
                          help='Report type')
        parser.add_argument('--export', action='store_true', help='Export data to JSON')
        parser.add_argument('--health-check', action='store_true', help='System health check')

    def handle(self, *args, **options):
        report_type = options['report']
        export_data = options['export']
        health_check = options['health_check']
        
        if health_check:
            self.run_health_check()
            return
        
        # Generate report
        report_data = self.generate_report(report_type)
        
        # Display report
        self.display_report(report_data, report_type)
        
        # Export if requested
        if export_data:
            self.export_report(report_data, report_type)

    def generate_report(self, report_type):
        """Generate analytics report"""
        now = timezone.now()
        
        if report_type == 'daily':
            start_date = now - timedelta(days=1)
            period_name = "Last 24 Hours"
        elif report_type == 'weekly':
            start_date = now - timedelta(days=7)
            period_name = "Last 7 Days"
        else:  # monthly
            start_date = now - timedelta(days=30)
            period_name = "Last 30 Days"
        
        # Get posts in period
        posts = Post.objects.filter(created_at__gte=start_date)
        published_posts = posts.filter(status='published')
        draft_posts = posts.filter(status='draft')
        
        # Calculate metrics
        report_data = {
            'period': period_name,
            'start_date': start_date.isoformat(),
            'end_date': now.isoformat(),
            'summary': {
                'total_posts': posts.count(),
                'published_posts': published_posts.count(),
                'draft_posts': draft_posts.count(),
                'publishing_rate': self.calculate_publishing_rate(published_posts, report_type),
                'avg_content_length': self.calculate_avg_content_length(published_posts),
                'total_views': sum(post.view_count for post in published_posts),
                'avg_views_per_post': self.calculate_avg_views(published_posts)
            },
            'categories': self.analyze_categories(published_posts),
            'tags': self.analyze_tags(published_posts),
            'content_quality': self.analyze_content_quality(published_posts),
            'publishing_schedule': self.analyze_publishing_schedule(published_posts),
            'recommendations': self.generate_recommendations(published_posts, report_type)
        }
        
        return report_data

    def calculate_publishing_rate(self, posts, report_type):
        """Calculate publishing rate"""
        count = posts.count()
        
        if report_type == 'daily':
            return f"{count} posts/day"
        elif report_type == 'weekly':
            rate = count / 7
            return f"{rate:.1f} posts/day ({count} posts/week)"
        else:  # monthly
            rate = count / 30
            return f"{rate:.1f} posts/day ({count} posts/month)"

    def calculate_avg_content_length(self, posts):
        """Calculate average content length"""
        if not posts:
            return 0
        
        total_length = sum(len(post.content) for post in posts)
        return total_length // posts.count()

    def calculate_avg_views(self, posts):
        """Calculate average views per post"""
        if not posts:
            return 0
        
        total_views = sum(post.view_count for post in posts)
        return total_views // posts.count()

    def analyze_categories(self, posts):
        """Analyze category distribution"""
        category_stats = {}
        
        for post in posts:
            for category in post.categories.all():
                if category.name not in category_stats:
                    category_stats[category.name] = {
                        'count': 0,
                        'total_views': 0,
                        'avg_content_length': 0
                    }
                
                category_stats[category.name]['count'] += 1
                category_stats[category.name]['total_views'] += post.view_count
        
        # Calculate averages
        for category, stats in category_stats.items():
            if stats['count'] > 0:
                stats['avg_views'] = stats['total_views'] // stats['count']
        
        # Sort by count
        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        
        return dict(sorted_categories)

    def analyze_tags(self, posts):
        """Analyze tag usage"""
        tag_stats = {}
        
        for post in posts:
            for tag in post.tags.all():
                if tag.name not in tag_stats:
                    tag_stats[tag.name] = 0
                tag_stats[tag.name] += 1
        
        # Sort by usage
        sorted_tags = sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_tags[:20])  # Top 20 tags

    def analyze_content_quality(self, posts):
        """Analyze content quality metrics"""
        if not posts:
            return {}
        
        content_lengths = [len(post.content) for post in posts]
        excerpt_lengths = [len(post.excerpt) if post.excerpt else 0 for post in posts]
        
        quality_metrics = {
            'avg_content_length': sum(content_lengths) // len(content_lengths),
            'min_content_length': min(content_lengths),
            'max_content_length': max(content_lengths),
            'posts_with_excerpts': sum(1 for post in posts if post.excerpt),
            'posts_with_images': sum(1 for post in posts if post.featured_image),
            'posts_allowing_comments': sum(1 for post in posts if post.allow_comments),
            'featured_posts': sum(1 for post in posts if post.is_featured)
        }
        
        # Quality score (0-100)
        quality_score = 0
        
        # Content length score (0-30)
        avg_length = quality_metrics['avg_content_length']
        if avg_length >= 15000:
            quality_score += 30
        elif avg_length >= 10000:
            quality_score += 25
        elif avg_length >= 5000:
            quality_score += 20
        elif avg_length >= 2000:
            quality_score += 15
        else:
            quality_score += 10
        
        # Excerpt score (0-20)
        excerpt_ratio = quality_metrics['posts_with_excerpts'] / len(posts)
        quality_score += int(excerpt_ratio * 20)
        
        # Image score (0-20)
        image_ratio = quality_metrics['posts_with_images'] / len(posts)
        quality_score += int(image_ratio * 20)
        
        # Engagement score (0-15)
        comment_ratio = quality_metrics['posts_allowing_comments'] / len(posts)
        quality_score += int(comment_ratio * 15)
        
        # Featured content score (0-15)
        featured_ratio = quality_metrics['featured_posts'] / len(posts)
        quality_score += int(featured_ratio * 15)
        
        quality_metrics['quality_score'] = min(quality_score, 100)
        
        return quality_metrics

    def analyze_publishing_schedule(self, posts):
        """Analyze publishing schedule patterns"""
        schedule_stats = {
            'by_day_of_week': {},
            'by_hour': {},
            'consistency_score': 0
        }
        
        for post in posts:
            # Day of week analysis
            day_name = post.created_at.strftime('%A')
            if day_name not in schedule_stats['by_day_of_week']:
                schedule_stats['by_day_of_week'][day_name] = 0
            schedule_stats['by_day_of_week'][day_name] += 1
            
            # Hour analysis
            hour = post.created_at.hour
            if hour not in schedule_stats['by_hour']:
                schedule_stats['by_hour'][hour] = 0
            schedule_stats['by_hour'][hour] += 1
        
        # Calculate consistency score
        if posts:
            days_with_posts = len(schedule_stats['by_day_of_week'])
            total_days = 7
            schedule_stats['consistency_score'] = int((days_with_posts / total_days) * 100)
        
        return schedule_stats

    def generate_recommendations(self, posts, report_type):
        """Generate actionable recommendations"""
        recommendations = []
        
        if not posts:
            recommendations.append("No posts found in this period. Consider increasing publishing frequency.")
            return recommendations
        
        # Publishing frequency recommendations
        post_count = posts.count()
        if report_type == 'weekly':
            if post_count < 2:
                recommendations.append("Consider increasing to 2-3 posts per week for better engagement.")
            elif post_count > 5:
                recommendations.append("High publishing frequency detected. Ensure quality is maintained.")
        
        # Content quality recommendations
        avg_length = sum(len(post.content) for post in posts) // post_count
        if avg_length < 5000:
            recommendations.append("Average content length is below 5000 characters. Consider creating more comprehensive posts.")
        
        # SEO recommendations
        posts_without_excerpts = sum(1 for post in posts if not post.excerpt)
        if posts_without_excerpts > 0:
            recommendations.append(f"{posts_without_excerpts} posts missing meta descriptions. Add excerpts for better SEO.")
        
        # Image recommendations
        posts_without_images = sum(1 for post in posts if not post.featured_image)
        if posts_without_images > 0:
            recommendations.append(f"{posts_without_images} posts missing featured images. Add images for better engagement.")
        
        # Category diversity
        categories = set()
        for post in posts:
            categories.update(post.categories.values_list('name', flat=True))
        
        if len(categories) < 3:
            recommendations.append("Consider diversifying content across more categories.")
        
        # Publishing schedule
        schedule_data = self.analyze_publishing_schedule(posts)
        if schedule_data['consistency_score'] < 50:
            recommendations.append("Publishing schedule could be more consistent. Consider using automated scheduling.")
        
        return recommendations

    def display_report(self, report_data, report_type):
        """Display formatted report"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"📊 PUBLISHING ANALYTICS REPORT - {report_data['period'].upper()}")
        self.stdout.write("="*60)
        
        # Summary
        summary = report_data['summary']
        self.stdout.write(f"\n📈 Summary:")
        self.stdout.write(f"   Total Posts: {summary['total_posts']}")
        self.stdout.write(f"   Published: {summary['published_posts']}")
        self.stdout.write(f"   Drafts: {summary['draft_posts']}")
        self.stdout.write(f"   Publishing Rate: {summary['publishing_rate']}")
        self.stdout.write(f"   Avg Content Length: {summary['avg_content_length']:,} characters")
        self.stdout.write(f"   Total Views: {summary['total_views']:,}")
        self.stdout.write(f"   Avg Views/Post: {summary['avg_views_per_post']}")
        
        # Content Quality
        quality = report_data['content_quality']
        if quality:
            self.stdout.write(f"\n🎯 Content Quality (Score: {quality['quality_score']}/100):")
            self.stdout.write(f"   Avg Length: {quality['avg_content_length']:,} chars")
            self.stdout.write(f"   Posts with Excerpts: {quality['posts_with_excerpts']}")
            self.stdout.write(f"   Posts with Images: {quality['posts_with_images']}")
            self.stdout.write(f"   Featured Posts: {quality['featured_posts']}")
        
        # Top Categories
        categories = report_data['categories']
        if categories:
            self.stdout.write(f"\n📂 Top Categories:")
            for category, stats in list(categories.items())[:5]:
                self.stdout.write(f"   {category}: {stats['count']} posts, {stats['avg_views']} avg views")
        
        # Top Tags
        tags = report_data['tags']
        if tags:
            self.stdout.write(f"\n🏷️ Top Tags:")
            for tag, count in list(tags.items())[:10]:
                self.stdout.write(f"   {tag}: {count} posts")
        
        # Publishing Schedule
        schedule = report_data['publishing_schedule']
        if schedule['by_day_of_week']:
            self.stdout.write(f"\n📅 Publishing by Day (Consistency: {schedule['consistency_score']}%):")
            for day, count in schedule['by_day_of_week'].items():
                self.stdout.write(f"   {day}: {count} posts")
        
        # Recommendations
        recommendations = report_data['recommendations']
        if recommendations:
            self.stdout.write(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f"   {i}. {rec}")
        
        self.stdout.write(f"\n✅ Report generated successfully!")

    def export_report(self, report_data, report_type):
        """Export report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"publishing_report_{report_type}_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.stdout.write(f"📄 Report exported to: {filename}")
            
        except Exception as e:
            self.stdout.write(f"❌ Export error: {str(e)}")

    def run_health_check(self):
        """Run system health check"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("🏥 SYSTEM HEALTH CHECK")
        self.stdout.write("="*60)
        
        health_status = {
            'overall': 'healthy',
            'issues': []
        }
        
        # Check API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            health_status['issues'].append("GEMINI_API_KEY not found in environment")
            health_status['overall'] = 'warning'
        else:
            self.stdout.write("✅ GEMINI_API_KEY configured")
        
        # Check recent publishing activity
        recent_posts = Post.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if recent_posts == 0:
            health_status['issues'].append("No posts published in the last 7 days")
            health_status['overall'] = 'warning'
        else:
            self.stdout.write(f"✅ {recent_posts} posts published in last 7 days")
        
        # Check draft posts
        draft_count = Post.objects.filter(status='draft').count()
        if draft_count > 10:
            health_status['issues'].append(f"High number of draft posts: {draft_count}")
        else:
            self.stdout.write(f"✅ Draft posts: {draft_count}")
        
        # Check content quality
        recent_published = Post.objects.filter(
            status='published',
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if recent_published:
            avg_length = sum(len(post.content) for post in recent_published) / recent_published.count()
            if avg_length < 5000:
                health_status['issues'].append(f"Average content length low: {avg_length:.0f} chars")
            else:
                self.stdout.write(f"✅ Average content length: {avg_length:.0f} chars")
            
            posts_without_images = sum(1 for post in recent_published if not post.featured_image)
            if posts_without_images > recent_published.count() * 0.5:
                health_status['issues'].append(f"{posts_without_images} posts missing images")
            else:
                self.stdout.write(f"✅ Posts with images: {recent_published.count() - posts_without_images}")
        
        # Check publishing log
        if os.path.exists('publishing_log.json'):
            self.stdout.write("✅ Publishing log found")
        else:
            health_status['issues'].append("Publishing log not found")
        
        # Overall status
        if health_status['overall'] == 'healthy':
            self.stdout.write(f"\n🎉 System Status: HEALTHY")
        else:
            self.stdout.write(f"\n⚠️ System Status: {health_status['overall'].upper()}")
        
        # Show issues
        if health_status['issues']:
            self.stdout.write(f"\n🔧 Issues to Address:")
            for i, issue in enumerate(health_status['issues'], 1):
                self.stdout.write(f"   {i}. {issue}")
        
        # Recommendations
        self.stdout.write(f"\n💡 Health Recommendations:")
        self.stdout.write(f"   • Run health check weekly")
        self.stdout.write(f"   • Monitor publishing logs")
        self.stdout.write(f"   • Keep API keys secure and updated")
        self.stdout.write(f"   • Maintain consistent publishing schedule")
        self.stdout.write(f"   • Review content quality metrics monthly")