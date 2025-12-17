"""
CRAG Content Generation Management Command

This command uses Corrective Retrieval-Augmented Generation (CRAG) to create
high-quality blog content that meets Google AdSense requirements.

Key Features:
- Knowledge retrieval from authoritative sources
- Iterative quality improvement
- AdSense compliance validation
- Automatic content optimization
- Comprehensive quality scoring
"""

import os
import time
import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from blog.services.crag_service import CRAGService
from blog.models import Post
from blog.content_quality import generate_quality_report

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate high-quality blog content using CRAG methodology for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', 
            type=int, 
            default=1, 
            help='Number of posts to generate (default: 1)'
        )
        parser.add_argument(
            '--topic', 
            type=str, 
            help='Specific topic to write about (optional)'
        )
        parser.add_argument(
            '--author', 
            type=str, 
            help='Author username or email (optional)'
        )
        parser.add_argument(
            '--publish', 
            action='store_true', 
            help='Publish posts immediately (default: save as draft)'
        )
        parser.add_argument(
            '--min-quality', 
            type=int, 
            default=85, 
            help='Minimum quality score required (default: 85)'
        )
        parser.add_argument(
            '--dry-run', 
            action='store_true', 
            help='Generate content but don\'t save to database'
        )
        parser.add_argument(
            '--verbose', 
            action='store_true', 
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        self.count = options['count']
        self.topic = options.get('topic')
        self.author_identifier = options.get('author')
        self.publish = options['publish']
        self.min_quality = options['min_quality']
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        
        # Initialize CRAG service
        try:
            self.crag_service = CRAGService()
            self.crag_service.min_quality_score = self.min_quality
        except ValueError as e:
            raise CommandError(f"CRAG service initialization failed: {e}")
        
        # Get or create author
        self.author = self._get_or_create_author()
        
        self.stdout.write(self.style.SUCCESS("🚀 Starting CRAG Content Generation"))
        self.stdout.write(f"   Target Quality: {self.min_quality}+/100")
        self.stdout.write(f"   Posts to Generate: {self.count}")
        self.stdout.write(f"   Mode: {'Publish' if self.publish else 'Draft'}")
        self.stdout.write(f"   Dry Run: {'Yes' if self.dry_run else 'No'}")
        
        if self.topic:
            self.stdout.write(f"   Specific Topic: {self.topic}")
        
        # Check daily limits
        if not self._check_daily_limits():
            self.stdout.write(
                self.style.WARNING("⚠️ Daily content generation limit reached (3 posts/day)")
            )
            return
        
        # Generate content
        success_count = 0
        total_time = 0
        
        for i in range(self.count):
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"📝 Generating Post {i + 1}/{self.count}")
            self.stdout.write(f"{'='*60}")
            
            start_time = time.time()
            
            try:
                post = self._generate_single_post(i + 1)
                
                if post:
                    success_count += 1
                    generation_time = time.time() - start_time
                    total_time += generation_time
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Successfully generated: {post.title}"
                        )
                    )
                    self.stdout.write(f"   Generation time: {generation_time:.1f}s")
                    
                    if self.verbose:
                        self._display_post_details(post)
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Failed to generate post {i + 1}")
                    )
                
                # Rate limiting between posts
                if i < self.count - 1:
                    self.stdout.write("⏳ Rate limiting (15s)...")
                    time.sleep(15)
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error generating post {i + 1}: {str(e)}")
                )
                if self.verbose:
                    import traceback
                    self.stdout.write(traceback.format_exc())
        
        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("📊 GENERATION SUMMARY")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"✅ Successful: {success_count}/{self.count}")
        self.stdout.write(f"⏱️ Total Time: {total_time:.1f}s")
        
        if success_count > 0:
            self.stdout.write(f"📈 Average Time: {total_time/success_count:.1f}s per post")
        
        if success_count == self.count:
            self.stdout.write(
                self.style.SUCCESS("🎉 All posts generated successfully!")
            )
        elif success_count > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Partial success: {success_count}/{self.count} posts")
            )
        else:
            self.stdout.write(
                self.style.ERROR("❌ No posts generated successfully")
            )

    def _generate_single_post(self, post_number: int) -> Post:
        """Generate a single high-quality post using CRAG"""
        
        # Get topic
        if self.topic:
            topic = self.topic
        else:
            topics = self.crag_service.get_trending_topics()
            topic = topics[(post_number - 1) % len(topics)]
        
        self.stdout.write(f"🎯 Topic: {topic}")
        
        # Generate content using CRAG
        self.stdout.write("🔍 Phase 1: Knowledge Retrieval...")
        self.stdout.write("🤖 Phase 2: Content Generation...")
        self.stdout.write("📊 Phase 3: Quality Assessment...")
        self.stdout.write("🔧 Phase 4: Corrective Refinement...")
        
        content_data = self.crag_service.generate_high_quality_content(
            topic=topic,
            target_audience="senior developers and tech leads"
        )
        
        if not content_data:
            self.stdout.write(self.style.ERROR("❌ CRAG content generation failed"))
            return None
        
        # Validate quality
        quality_report = generate_quality_report(
            content_data['content'],
            content_data['title'], 
            content_data['excerpt']
        )
        
        quality_score = quality_report['score']
        self.stdout.write(f"📊 Final Quality Score: {quality_score:.1f}/100")
        
        if quality_score < self.min_quality:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ Quality below threshold ({self.min_quality}), but proceeding..."
                )
            )
        
        # Display quality details
        if self.verbose:
            self._display_quality_details(quality_report)
        
        # Create post if not dry run
        if self.dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN: Post not saved"))
            return None
        
        # Create post
        post = self.crag_service.create_post_from_crag_content(content_data, self.author)
        
        if not post:
            self.stdout.write(self.style.ERROR("❌ Failed to create post object"))
            return None
        
        # Set status
        if self.publish and quality_score >= self.min_quality:
            post.status = 'published'
            post.save()
            self.stdout.write("📢 Status: Published")
        else:
            post.status = 'draft'
            post.save()
            self.stdout.write("📝 Status: Draft (review recommended)")
        
        return post

    def _get_or_create_author(self):
        """Get or create author for posts"""
        if self.author_identifier:
            try:
                # Try to find by username first
                return User.objects.get(username=self.author_identifier)
            except User.DoesNotExist:
                try:
                    # Try to find by email
                    return User.objects.get(email=self.author_identifier)
                except User.DoesNotExist:
                    raise CommandError(f"Author not found: {self.author_identifier}")
        else:
            # Get first superuser or create default
            superuser = User.objects.filter(is_superuser=True).first()
            if superuser:
                return superuser
            else:
                raise CommandError("No superuser found. Please specify --author or create a superuser.")

    def _check_daily_limits(self) -> bool:
        """Check if daily content generation limits are reached"""
        today = timezone.now().date()
        today_posts = Post.objects.filter(
            created_at__date=today,
            status__in=['published', 'draft']
        ).count()
        
        # Limit to 3 posts per day to avoid spam
        return today_posts < 3

    def _display_post_details(self, post: Post):
        """Display detailed post information"""
        self.stdout.write("📋 POST DETAILS:")
        self.stdout.write(f"   Title: {post.title}")
        self.stdout.write(f"   Slug: {post.slug}")
        self.stdout.write(f"   Excerpt: {post.excerpt[:100]}...")
        self.stdout.write(f"   Word Count: {len(post.content.split())} words")
        self.stdout.write(f"   Categories: {', '.join(post.categories.values_list('name', flat=True))}")
        self.stdout.write(f"   Tags: {', '.join(post.tags.values_list('name', flat=True))}")
        self.stdout.write(f"   Status: {post.status}")
        self.stdout.write(f"   Created: {post.created_at}")

    def _display_quality_details(self, quality_report: dict):
        """Display detailed quality assessment"""
        self.stdout.write("📊 QUALITY ASSESSMENT:")
        self.stdout.write(f"   Overall Score: {quality_report['score']:.1f}/100")
        
        if 'word_count' in quality_report:
            self.stdout.write(f"   Word Count: {quality_report['word_count']}")
        
        if 'readability_score' in quality_report:
            self.stdout.write(f"   Readability: {quality_report['readability_score']:.1f}")
        
        if 'structure_score' in quality_report:
            self.stdout.write(f"   Structure: {quality_report['structure_score']:.1f}")
        
        # Display issues if any
        issues = quality_report.get('issues', [])
        if issues:
            self.stdout.write("   Issues:")
            for issue in issues[:5]:  # Show first 5 issues
                self.stdout.write(f"     - {issue}")
        
        # Display CRAG-specific metrics
        crag_issues = quality_report.get('crag_issues', [])
        if crag_issues:
            self.stdout.write("   CRAG Issues:")
            for issue in crag_issues:
                self.stdout.write(f"     - {issue}")

    def _log_generation_stats(self, success_count: int, total_count: int, total_time: float):
        """Log generation statistics for monitoring"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': (success_count / total_count) * 100 if total_count > 0 else 0,
            'total_time': total_time,
            'average_time': total_time / success_count if success_count > 0 else 0,
            'min_quality_threshold': self.min_quality,
            'mode': 'publish' if self.publish else 'draft'
        }
        
        logger.info(f"CRAG content generation completed: {stats}")
        
        # Could also save to database or external monitoring system
        # self._save_generation_metrics(stats)