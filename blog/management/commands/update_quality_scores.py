"""
Update Quality Scores Management Command

This command updates quality scores for all blog posts and is used by Django Beat tasks.
It provides comprehensive quality monitoring and generates reports for content improvement.

Features:
- Updates quality scores for all posts
- Identifies posts needing improvement
- Generates quality reports
- Tracks quality trends over time
- Sends alerts for low-quality content

Usage:
- Called automatically by Django Beat daily_quality_update task
- Can be run manually for immediate updates
- Used by Celery tasks for automated quality monitoring
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, Count, Q

from blog.models import Post
from blog.services.adsense_quality_checker import AdSenseQualityChecker
from blog.content_quality import generate_quality_report

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update quality scores for all blog posts (used by Django Beat tasks and manual execution)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--posts-per-run',
            type=int,
            default=50,
            help='Maximum number of posts to process per run (default: 50)'
        )
        parser.add_argument(
            '--min-quality-threshold',
            type=int,
            default=75,
            help='Minimum quality threshold for alerts (default: 75)'
        )
        parser.add_argument(
            '--only-published',
            action='store_true',
            help='Only process published posts'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update all posts, ignoring cache'
        )
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate detailed quality report'
        )
        parser.add_argument(
            '--alert-low-quality',
            action='store_true',
            help='Send alerts for low-quality posts'
        )
        parser.add_argument(
            '--save-history',
            action='store_true',
            help='Save quality score history for trending analysis'
        )

    def handle(self, *args, **options):
        self.posts_per_run = options['posts_per_run']
        self.min_quality_threshold = options['min_quality_threshold']
        self.only_published = options['only_published']
        self.force_update = options['force_update']
        self.generate_report = options['generate_report']
        self.alert_low_quality = options['alert_low_quality']
        self.save_history = options['save_history']
        
        # Initialize quality checker
        self.adsense_checker = AdSenseQualityChecker()
        
        self.stdout.write(self.style.SUCCESS("📊 Starting Daily Quality Score Update"))
        self.stdout.write("=" * 60)
        
        # Get posts to process
        posts_to_process = self._get_posts_to_process()
        
        if not posts_to_process:
            self.stdout.write("✅ No posts need quality score updates")
            return
        
        self.stdout.write(f"🎯 Processing {len(posts_to_process)} posts...")
        
        # Process posts and update scores
        results = self._process_posts(posts_to_process)
        
        # Generate summary report
        self._generate_summary_report(results)
        
        # Generate detailed report if requested
        if self.generate_report:
            self._generate_detailed_report(results)
        
        # Send alerts for low-quality posts
        if self.alert_low_quality:
            self._send_quality_alerts(results)
        
        # Save quality history
        if self.save_history:
            self._save_quality_history(results)
        
        self.stdout.write(self.style.SUCCESS("✅ Quality score update completed!"))

    def _get_posts_to_process(self) -> List[Post]:
        """Get posts that need quality score updates"""
        
        # Base queryset
        if self.only_published:
            queryset = Post.objects.filter(status='published')
        else:
            queryset = Post.objects.filter(status__in=['published', 'draft'])
        
        # If not forcing update, only get posts that haven't been checked recently
        if not self.force_update:
            # Check posts that haven't been updated in the last 24 hours
            cache_cutoff = timezone.now() - timedelta(hours=24)
            
            # Get posts without recent quality checks
            posts_needing_update = []
            for post in queryset.order_by('-updated_at')[:self.posts_per_run * 2]:
                cache_key = f"quality_score_{post.id}"
                last_check = cache.get(f"{cache_key}_timestamp")
                
                if not last_check or datetime.fromisoformat(last_check) < cache_cutoff:
                    posts_needing_update.append(post)
                
                if len(posts_needing_update) >= self.posts_per_run:
                    break
            
            return posts_needing_update
        else:
            # Force update - get all posts up to limit
            return list(queryset.order_by('-updated_at')[:self.posts_per_run])

    def _process_posts(self, posts: List[Post]) -> Dict:
        """Process posts and update their quality scores"""
        
        results = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
            'excellent_posts': [],
            'good_posts': [],
            'poor_posts': [],
            'failed_posts': [],
            'total_score': 0,
            'score_distribution': {
                'excellent': 0,  # 90+
                'good': 0,       # 75-89
                'fair': 0,       # 60-74
                'poor': 0        # <60
            }
        }
        
        for i, post in enumerate(posts, 1):
            try:
                self.stdout.write(f"📝 Processing {i}/{len(posts)}: {post.title[:50]}...")
                
                # Generate comprehensive quality assessment
                quality_report = self.adsense_checker.comprehensive_quality_assessment(
                    post.content, post.title, post.excerpt or ''
                )
                
                quality_score = quality_report['overall_score']
                results['total_score'] += quality_score
                results['processed'] += 1
                
                # Cache the quality score and timestamp
                cache_key = f"quality_score_{post.id}"
                cache.set(cache_key, quality_score, 86400)  # Cache for 24 hours
                cache.set(f"{cache_key}_timestamp", datetime.now().isoformat(), 86400)
                cache.set(f"{cache_key}_report", quality_report, 86400)
                
                # Categorize post quality
                post_info = {
                    'id': post.id,
                    'title': post.title,
                    'score': quality_score,
                    'word_count': len(post.content.split()),
                    'status': post.status,
                    'created_at': post.created_at,
                    'adsense_ready': quality_report.get('adsense_ready', False),
                    'issues': quality_report.get('issues', [])[:3]
                }
                
                # Update score distribution
                if quality_score >= 90:
                    results['excellent_posts'].append(post_info)
                    results['score_distribution']['excellent'] += 1
                elif quality_score >= 75:
                    results['good_posts'].append(post_info)
                    results['score_distribution']['good'] += 1
                elif quality_score >= 60:
                    results['score_distribution']['fair'] += 1
                else:
                    results['poor_posts'].append(post_info)
                    results['score_distribution']['poor'] += 1
                
                results['updated'] += 1
                
                self.stdout.write(f"   ✅ Score: {quality_score:.1f}/100")
                
            except Exception as e:
                self.stdout.write(f"   ❌ Error: {str(e)}")
                results['failed'] += 1
                results['failed_posts'].append({
                    'id': post.id,
                    'title': post.title,
                    'error': str(e)
                })
                logger.error(f"Failed to process post {post.id}: {str(e)}")
        
        return results

    def _generate_summary_report(self, results: Dict):
        """Generate and display summary report"""
        
        processed = results['processed']
        updated = results['updated']
        failed = results['failed']
        
        if processed > 0:
            average_score = results['total_score'] / processed
        else:
            average_score = 0
        
        self.stdout.write(f"\n📊 QUALITY UPDATE SUMMARY")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Posts Processed: {processed}")
        self.stdout.write(f"Successfully Updated: {updated}")
        self.stdout.write(f"Failed: {failed}")
        self.stdout.write(f"Average Quality Score: {average_score:.1f}/100")
        
        # Score distribution
        distribution = results['score_distribution']
        self.stdout.write(f"\n📈 QUALITY DISTRIBUTION")
        self.stdout.write("-" * 40)
        self.stdout.write(f"🟢 Excellent (90+): {distribution['excellent']} posts")
        self.stdout.write(f"🟡 Good (75-89): {distribution['good']} posts")
        self.stdout.write(f"🟠 Fair (60-74): {distribution['fair']} posts")
        self.stdout.write(f"🔴 Poor (<60): {distribution['poor']} posts")
        
        # Quality alerts
        poor_count = len(results['poor_posts'])
        if poor_count > 0:
            self.stdout.write(f"\n⚠️ QUALITY ALERTS")
            self.stdout.write("-" * 40)
            self.stdout.write(f"🔴 {poor_count} posts below quality threshold")
            
            # Show worst performing posts
            worst_posts = sorted(results['poor_posts'], key=lambda x: x['score'])[:5]
            for post in worst_posts:
                self.stdout.write(f"   - {post['title'][:40]}... (Score: {post['score']:.1f})")

    def _generate_detailed_report(self, results: Dict):
        """Generate detailed quality report and save to file"""
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'processed': results['processed'],
                'updated': results['updated'],
                'failed': results['failed'],
                'average_score': results['total_score'] / results['processed'] if results['processed'] > 0 else 0,
                'score_distribution': results['score_distribution']
            },
            'excellent_posts': results['excellent_posts'],
            'good_posts': results['good_posts'],
            'poor_posts': results['poor_posts'],
            'failed_posts': results['failed_posts']
        }
        
        # Save report to file
        report_filename = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.stdout.write(f"\n📄 Detailed report saved: {report_filename}")
            
        except Exception as e:
            self.stdout.write(f"\n❌ Failed to save detailed report: {str(e)}")

    def _send_quality_alerts(self, results: Dict):
        """Send alerts for low-quality posts"""
        
        poor_posts = results['poor_posts']
        
        if not poor_posts:
            self.stdout.write(f"\n✅ No quality alerts needed")
            return
        
        self.stdout.write(f"\n🚨 QUALITY ALERTS")
        self.stdout.write("-" * 40)
        
        # Group alerts by severity
        critical_posts = [p for p in poor_posts if p['score'] < 50]
        warning_posts = [p for p in poor_posts if 50 <= p['score'] < self.min_quality_threshold]
        
        if critical_posts:
            self.stdout.write(f"🔴 CRITICAL ({len(critical_posts)} posts):")
            for post in critical_posts[:5]:
                self.stdout.write(f"   - {post['title'][:50]}... (Score: {post['score']:.1f})")
                if post['issues']:
                    self.stdout.write(f"     Issues: {', '.join(post['issues'][:2])}")
        
        if warning_posts:
            self.stdout.write(f"⚠️ WARNING ({len(warning_posts)} posts):")
            for post in warning_posts[:5]:
                self.stdout.write(f"   - {post['title'][:50]}... (Score: {post['score']:.1f})")
        
        # Recommendations
        self.stdout.write(f"\n💡 RECOMMENDATIONS:")
        self.stdout.write(f"   1. Regenerate critical posts using CRAG:")
        self.stdout.write(f"      python manage.py upgrade_to_crag --regenerate-low-quality --max-posts 5")
        self.stdout.write(f"   2. Review and improve warning posts manually")
        self.stdout.write(f"   3. Use CRAG for all new content generation")

    def _save_quality_history(self, results: Dict):
        """Save quality score history for trend analysis"""
        
        history_data = {
            'date': datetime.now().date().isoformat(),
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_posts': results['processed'],
                'average_score': results['total_score'] / results['processed'] if results['processed'] > 0 else 0,
                'score_distribution': results['score_distribution'],
                'excellent_count': len(results['excellent_posts']),
                'good_count': len(results['good_posts']),
                'poor_count': len(results['poor_posts'])
            }
        }
        
        # Save to cache for trend analysis
        history_key = f"quality_history_{datetime.now().strftime('%Y%m%d')}"
        cache.set(history_key, history_data, 86400 * 30)  # Keep for 30 days
        
        # Also maintain a rolling history
        rolling_history_key = "quality_rolling_history"
        rolling_history = cache.get(rolling_history_key, [])
        rolling_history.append(history_data)
        
        # Keep only last 30 days
        if len(rolling_history) > 30:
            rolling_history = rolling_history[-30:]
        
        cache.set(rolling_history_key, rolling_history, 86400 * 30)
        
        self.stdout.write(f"\n📈 Quality history saved for trend analysis")

    def get_quality_trends(self, days: int = 7) -> Dict:
        """Get quality trends for the last N days"""
        
        rolling_history = cache.get("quality_rolling_history", [])
        
        if len(rolling_history) < 2:
            return {'trend': 'insufficient_data', 'message': 'Not enough historical data'}
        
        # Get recent data
        recent_data = rolling_history[-days:] if len(rolling_history) >= days else rolling_history
        
        if len(recent_data) < 2:
            return {'trend': 'insufficient_data', 'message': 'Not enough recent data'}
        
        # Calculate trend
        first_score = recent_data[0]['summary']['average_score']
        last_score = recent_data[-1]['summary']['average_score']
        
        score_change = last_score - first_score
        
        trend_data = {
            'period_days': len(recent_data),
            'first_score': first_score,
            'last_score': last_score,
            'score_change': score_change,
            'trend': 'improving' if score_change > 2 else 'declining' if score_change < -2 else 'stable',
            'daily_scores': [d['summary']['average_score'] for d in recent_data]
        }
        
        return trend_data


# Utility function for external use
def get_post_quality_score(post_id: int) -> float:
    """Get cached quality score for a post"""
    cache_key = f"quality_score_{post_id}"
    return cache.get(cache_key, 0.0)


def get_quality_report(post_id: int) -> Dict:
    """Get cached quality report for a post"""
    cache_key = f"quality_score_{post_id}_report"
    return cache.get(cache_key, {})


def get_site_quality_summary() -> Dict:
    """Get overall site quality summary"""
    rolling_history = cache.get("quality_rolling_history", [])
    
    if not rolling_history:
        return {'status': 'no_data', 'message': 'No quality data available'}
    
    latest = rolling_history[-1]
    
    return {
        'last_updated': latest['timestamp'],
        'average_score': latest['summary']['average_score'],
        'total_posts': latest['summary']['total_posts'],
        'score_distribution': latest['summary']['score_distribution'],
        'quality_status': 'excellent' if latest['summary']['average_score'] >= 85 else 
                         'good' if latest['summary']['average_score'] >= 75 else 
                         'needs_improvement'
    }