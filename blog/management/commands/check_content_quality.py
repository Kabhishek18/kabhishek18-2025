"""
Management command to check content quality for existing posts
"""

from django.core.management.base import BaseCommand
from blog.models import Post
from blog.content_quality import generate_quality_report
import json


class Command(BaseCommand):
    help = 'Check content quality for blog posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--post-id',
            type=int,
            help='Check specific post by ID'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all published posts'
        )
        parser.add_argument(
            '--draft',
            action='store_true',
            help='Check draft posts'
        )
        parser.add_argument(
            '--min-score',
            type=int,
            default=70,
            help='Minimum quality score (default: 70)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed report'
        )

    def handle(self, *args, **options):
        post_id = options.get('post_id')
        check_all = options.get('all')
        check_draft = options.get('draft')
        min_score = options.get('min_score')
        detailed = options.get('detailed')

        if post_id:
            posts = Post.objects.filter(id=post_id)
        elif check_all:
            posts = Post.objects.filter(status='published')
        elif check_draft:
            posts = Post.objects.filter(status='draft')
        else:
            self.stdout.write(self.style.ERROR('Please specify --post-id, --all, or --draft'))
            return

        if not posts.exists():
            self.stdout.write(self.style.WARNING('No posts found'))
            return

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"Checking {posts.count()} post(s) for content quality...")
        self.stdout.write(f"{'='*80}\n")

        passed_count = 0
        failed_count = 0
        
        for post in posts:
            self.stdout.write(f"\n📝 Post: {post.title}")
            self.stdout.write(f"   ID: {post.id} | Status: {post.status}")
            
            # Generate quality report
            report = generate_quality_report(
                content=post.content,
                title=post.title,
                excerpt=post.excerpt
            )
            
            # Display score
            score = report['score']
            if score >= 90:
                score_style = self.style.SUCCESS
                emoji = "🌟"
            elif score >= min_score:
                score_style = self.style.SUCCESS
                emoji = "✅"
            elif score >= 50:
                score_style = self.style.WARNING
                emoji = "⚠️"
            else:
                score_style = self.style.ERROR
                emoji = "❌"
            
            self.stdout.write(f"   {emoji} Quality Score: {score_style(f'{score:.1f}/100')}")
            
            if report['passed']:
                passed_count += 1
            else:
                failed_count += 1
            
            # Display key metrics
            if detailed or not report['passed']:
                self.stdout.write(f"\n   📊 Metrics:")
                
                for metric_name, metric_data in report['metrics'].items():
                    if isinstance(metric_data, dict):
                        value = metric_data.get('value', 'N/A')
                        metric_score = metric_data.get('score', 0)
                        
                        if metric_name == 'word_count':
                            self.stdout.write(f"      • Word Count: {value} words (Score: {metric_score:.0f})")
                        elif metric_name == 'readability':
                            interp = metric_data.get('interpretation', '')
                            self.stdout.write(f"      • Readability: {value} - {interp} (Score: {metric_score:.0f})")
                        elif metric_name == 'structure':
                            if isinstance(value, dict):
                                self.stdout.write(f"      • Structure: H2={value.get('h2_headings', 0)}, "
                                                f"Lists={value.get('lists', 0)}, "
                                                f"Paragraphs={value.get('paragraphs', 0)} "
                                                f"(Score: {metric_score:.0f})")
                
                # Display issues
                if report['issues']:
                    self.stdout.write(f"\n   ❌ Issues:")
                    for issue in report['issues']:
                        self.stdout.write(f"      • {issue}")
                
                # Display warnings
                if report['warnings']:
                    self.stdout.write(f"\n   ⚠️  Warnings:")
                    for warning in report['warnings']:
                        self.stdout.write(f"      • {warning}")
                
                # Display recommendations
                if detailed and report['recommendations']:
                    self.stdout.write(f"\n   💡 Recommendations:")
                    for rec in report['recommendations'][:3]:  # Show top 3
                        self.stdout.write(f"      • {rec}")
                
                # Display plagiarism results
                if 'plagiarism' in report:
                    plag = report['plagiarism']
                    if plag['matches_found'] > 0:
                        self.stdout.write(f"\n   🔍 Similarity Check:")
                        self.stdout.write(f"      • Uniqueness: {plag['uniqueness_score']:.0f}%")
                        self.stdout.write(f"      • Similar posts found: {plag['matches_found']}")
                        if detailed:
                            for match in plag['similar_posts'][:3]:
                                self.stdout.write(f"        - {match['title']} ({match['similarity']:.1f}% similar)")
            
            self.stdout.write("")  # Blank line

        # Summary
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"Summary:")
        self.stdout.write(f"  ✅ Passed: {passed_count}")
        self.stdout.write(f"  ❌ Failed: {failed_count}")
        self.stdout.write(f"  📊 Total: {posts.count()}")
        self.stdout.write(f"{'='*80}\n")
