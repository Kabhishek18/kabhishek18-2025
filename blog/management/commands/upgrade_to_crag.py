"""
Upgrade to CRAG Content Generation

This command helps transition from basic automatic content generation
to CRAG (Corrective Retrieval-Augmented Generation) for AdSense compliance.

Features:
- Audit existing content quality
- Identify low-quality posts
- Regenerate content using CRAG
- Update publishing configuration
- Provide AdSense readiness report
"""

import os
import json
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model

from blog.models import Post, Category, Tag
from blog.services.crag_service import CRAGService
from blog.services.adsense_quality_checker import AdSenseQualityChecker
from blog.content_quality import generate_quality_report

User = get_user_model()


class Command(BaseCommand):
    help = 'Upgrade content generation system to CRAG for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--audit-only',
            action='store_true',
            help='Only audit existing content, don\'t make changes'
        )
        parser.add_argument(
            '--regenerate-low-quality',
            action='store_true',
            help='Regenerate posts with quality score below threshold'
        )
        parser.add_argument(
            '--min-quality',
            type=int,
            default=75,
            help='Minimum quality score threshold (default: 75)'
        )
        parser.add_argument(
            '--max-posts',
            type=int,
            default=10,
            help='Maximum number of posts to regenerate (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--update-config',
            action='store_true',
            help='Update auto-publishing configuration to use CRAG'
        )

    def handle(self, *args, **options):
        self.audit_only = options['audit_only']
        self.regenerate = options['regenerate_low_quality']
        self.min_quality = options['min_quality']
        self.max_posts = options['max_posts']
        self.dry_run = options['dry_run']
        self.update_config = options['update_config']

        self.stdout.write(self.style.SUCCESS("🚀 CRAG Content Generation Upgrade"))
        self.stdout.write("=" * 60)
        
        # Initialize services
        try:
            self.crag_service = CRAGService()
            self.adsense_checker = AdSenseQualityChecker()
        except Exception as e:
            raise CommandError(f"Failed to initialize CRAG services: {e}")

        # Step 1: Audit existing content
        self.stdout.write("\n📊 Step 1: Auditing Existing Content")
        audit_results = self._audit_existing_content()
        self._display_audit_results(audit_results)

        # Step 2: Regenerate low-quality content (if requested)
        if self.regenerate and not self.audit_only:
            self.stdout.write("\n🔧 Step 2: Regenerating Low-Quality Content")
            regeneration_results = self._regenerate_low_quality_posts(audit_results)
            self._display_regeneration_results(regeneration_results)

        # Step 3: Update configuration (if requested)
        if self.update_config and not self.audit_only:
            self.stdout.write("\n⚙️ Step 3: Updating Configuration")
            self._update_publishing_configuration()

        # Step 4: AdSense readiness report
        self.stdout.write("\n📈 Step 4: AdSense Readiness Report")
        self._generate_adsense_report(audit_results)

        # Step 5: Recommendations
        self.stdout.write("\n💡 Step 5: Recommendations")
        self._provide_recommendations(audit_results)

    def _audit_existing_content(self):
        """Audit all existing published content"""
        self.stdout.write("   Analyzing published posts...")
        
        posts = Post.objects.filter(status='published').order_by('-created_at')
        
        audit_results = {
            'total_posts': posts.count(),
            'excellent_posts': [],
            'good_posts': [],
            'poor_posts': [],
            'failed_posts': [],
            'average_score': 0,
            'adsense_ready_count': 0
        }
        
        total_score = 0
        processed_count = 0
        
        for post in posts:
            try:
                # Use AdSense quality checker for comprehensive assessment
                quality_report = self.adsense_checker.comprehensive_quality_assessment(
                    post.content, post.title, post.excerpt
                )
                
                score = quality_report['overall_score']
                total_score += score
                processed_count += 1
                
                post_info = {
                    'id': post.id,
                    'title': post.title,
                    'score': score,
                    'word_count': len(post.content.split()),
                    'created_at': post.created_at,
                    'adsense_ready': quality_report['adsense_ready'],
                    'issues': quality_report['issues'][:3]  # Top 3 issues
                }
                
                if quality_report['adsense_ready']:
                    audit_results['adsense_ready_count'] += 1
                
                # Categorize posts
                if score >= 90:
                    audit_results['excellent_posts'].append(post_info)
                elif score >= self.min_quality:
                    audit_results['good_posts'].append(post_info)
                else:
                    audit_results['poor_posts'].append(post_info)
                    
            except Exception as e:
                self.stdout.write(f"   ⚠️ Failed to analyze post {post.id}: {str(e)}")
                audit_results['failed_posts'].append({
                    'id': post.id,
                    'title': post.title,
                    'error': str(e)
                })
        
        if processed_count > 0:
            audit_results['average_score'] = total_score / processed_count
        
        return audit_results

    def _display_audit_results(self, results):
        """Display audit results in a formatted way"""
        total = results['total_posts']
        excellent = len(results['excellent_posts'])
        good = len(results['good_posts'])
        poor = len(results['poor_posts'])
        failed = len(results['failed_posts'])
        
        self.stdout.write(f"\n   📊 AUDIT RESULTS:")
        self.stdout.write(f"   Total Posts: {total}")
        self.stdout.write(f"   Average Quality Score: {results['average_score']:.1f}/100")
        self.stdout.write(f"   AdSense Ready: {results['adsense_ready_count']}/{total} ({results['adsense_ready_count']/total*100:.1f}%)")
        
        self.stdout.write(f"\n   📈 QUALITY BREAKDOWN:")
        self.stdout.write(f"   🟢 Excellent (90+): {excellent} posts")
        self.stdout.write(f"   🟡 Good ({self.min_quality}+): {good} posts")
        self.stdout.write(f"   🔴 Poor (<{self.min_quality}): {poor} posts")
        
        if failed > 0:
            self.stdout.write(f"   ❌ Analysis Failed: {failed} posts")
        
        # Show worst performing posts
        if results['poor_posts']:
            self.stdout.write(f"\n   🔴 LOWEST QUALITY POSTS:")
            sorted_poor = sorted(results['poor_posts'], key=lambda x: x['score'])
            for post in sorted_poor[:5]:
                self.stdout.write(f"   - {post['title'][:50]}... (Score: {post['score']:.1f})")
                if post['issues']:
                    self.stdout.write(f"     Issues: {', '.join(post['issues'][:2])}")

    def _regenerate_low_quality_posts(self, audit_results):
        """Regenerate low-quality posts using CRAG"""
        poor_posts = audit_results['poor_posts']
        
        if not poor_posts:
            self.stdout.write("   ✅ No low-quality posts found to regenerate")
            return {'regenerated': 0, 'failed': 0, 'skipped': 0}
        
        # Limit number of posts to regenerate
        posts_to_regenerate = poor_posts[:self.max_posts]
        
        self.stdout.write(f"   🎯 Regenerating {len(posts_to_regenerate)} posts...")
        
        results = {'regenerated': 0, 'failed': 0, 'skipped': 0}
        
        for post_info in posts_to_regenerate:
            try:
                post = Post.objects.get(id=post_info['id'])
                
                self.stdout.write(f"\n   🔄 Regenerating: {post.title[:50]}...")
                self.stdout.write(f"      Current Score: {post_info['score']:.1f}/100")
                
                if self.dry_run:
                    self.stdout.write("      🔍 DRY RUN: Would regenerate this post")
                    results['skipped'] += 1
                    continue
                
                # Generate new content using CRAG
                new_content = self.crag_service.generate_high_quality_content(
                    topic=post.title,  # Use existing title as topic
                    target_audience="developers and tech professionals"
                )
                
                if not new_content:
                    self.stdout.write("      ❌ Failed to generate new content")
                    results['failed'] += 1
                    continue
                
                # Backup original content
                original_content = {
                    'title': post.title,
                    'content': post.content,
                    'excerpt': post.excerpt,
                    'backup_date': datetime.now().isoformat()
                }
                
                # Update post with new content (keep original title)
                post.content = new_content['content']
                post.excerpt = new_content['excerpt']
                post.status = 'draft'  # Set to draft for review
                
                # Store backup in meta_data
                if post.meta_data:
                    try:
                        meta = json.loads(post.meta_data)
                    except:
                        meta = {}
                else:
                    meta = {}
                
                meta['crag_backup'] = original_content
                post.meta_data = json.dumps(meta)
                
                post.save()
                
                # Check new quality
                new_quality = self.adsense_checker.comprehensive_quality_assessment(
                    post.content, post.title, post.excerpt
                )
                
                improvement = new_quality['overall_score'] - post_info['score']
                
                self.stdout.write(f"      ✅ Regenerated successfully")
                self.stdout.write(f"      📈 New Score: {new_quality['overall_score']:.1f}/100 (+{improvement:.1f})")
                self.stdout.write(f"      📝 Status: Draft (review recommended)")
                
                results['regenerated'] += 1
                
            except Exception as e:
                self.stdout.write(f"      ❌ Error: {str(e)}")
                results['failed'] += 1
        
        return results

    def _display_regeneration_results(self, results):
        """Display regeneration results"""
        total = results['regenerated'] + results['failed'] + results['skipped']
        
        self.stdout.write(f"\n   📊 REGENERATION RESULTS:")
        self.stdout.write(f"   ✅ Successfully Regenerated: {results['regenerated']}")
        self.stdout.write(f"   ❌ Failed: {results['failed']}")
        self.stdout.write(f"   ⏭️ Skipped (dry run): {results['skipped']}")
        
        if results['regenerated'] > 0:
            self.stdout.write(f"\n   📝 NOTE: Regenerated posts are saved as DRAFTS for review")
            self.stdout.write(f"   🔄 Original content backed up in post meta_data")

    def _update_publishing_configuration(self):
        """Update auto-publishing configuration to use CRAG"""
        config_file = 'auto_publishing_config.json'
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update configuration for CRAG
            config.update({
                'content_generation_method': 'crag',
                'quality_threshold': 85,
                'min_word_count': 1200,
                'use_adsense_compliance': True,
                'updated_at': datetime.now().isoformat(),
                'crag_settings': {
                    'max_retries': 3,
                    'quality_correction_enabled': True,
                    'knowledge_retrieval_enabled': True,
                    'target_audience': 'developers and tech professionals'
                }
            })
            
            if not self.dry_run:
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                self.stdout.write("   ✅ Configuration updated successfully")
            else:
                self.stdout.write("   🔍 DRY RUN: Would update configuration")
            
            self.stdout.write("   📋 New Configuration:")
            self.stdout.write(f"      Content Method: CRAG")
            self.stdout.write(f"      Quality Threshold: {config['quality_threshold']}")
            self.stdout.write(f"      Min Word Count: {config['min_word_count']}")
            self.stdout.write(f"      AdSense Compliance: Enabled")
            
        except Exception as e:
            self.stdout.write(f"   ❌ Failed to update configuration: {str(e)}")

    def _generate_adsense_report(self, audit_results):
        """Generate AdSense readiness report"""
        total_posts = audit_results['total_posts']
        adsense_ready = audit_results['adsense_ready_count']
        average_score = audit_results['average_score']
        
        # AdSense readiness criteria
        min_posts_needed = 20  # Google typically wants 20+ quality posts
        min_average_score = 80
        min_ready_percentage = 80
        
        ready_percentage = (adsense_ready / total_posts * 100) if total_posts > 0 else 0
        
        self.stdout.write(f"   📊 ADSENSE READINESS ASSESSMENT:")
        self.stdout.write(f"   Posts Ready for AdSense: {adsense_ready}/{total_posts} ({ready_percentage:.1f}%)")
        self.stdout.write(f"   Average Quality Score: {average_score:.1f}/100")
        
        # Check criteria
        criteria_met = 0
        total_criteria = 4
        
        self.stdout.write(f"\n   ✅ READINESS CRITERIA:")
        
        # Criterion 1: Minimum number of posts
        if total_posts >= min_posts_needed:
            self.stdout.write(f"   ✅ Post Count: {total_posts} (minimum: {min_posts_needed})")
            criteria_met += 1
        else:
            needed = min_posts_needed - total_posts
            self.stdout.write(f"   ❌ Post Count: {total_posts} (need {needed} more)")
        
        # Criterion 2: Average quality score
        if average_score >= min_average_score:
            self.stdout.write(f"   ✅ Average Quality: {average_score:.1f} (minimum: {min_average_score})")
            criteria_met += 1
        else:
            self.stdout.write(f"   ❌ Average Quality: {average_score:.1f} (minimum: {min_average_score})")
        
        # Criterion 3: Percentage of ready posts
        if ready_percentage >= min_ready_percentage:
            self.stdout.write(f"   ✅ Ready Posts: {ready_percentage:.1f}% (minimum: {min_ready_percentage}%)")
            criteria_met += 1
        else:
            self.stdout.write(f"   ❌ Ready Posts: {ready_percentage:.1f}% (minimum: {min_ready_percentage}%)")
        
        # Criterion 4: No recent low-quality posts
        recent_posts = Post.objects.filter(
            status='published',
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if recent_posts.exists():
            recent_quality_scores = []
            for post in recent_posts:
                try:
                    quality = self.adsense_checker.comprehensive_quality_assessment(
                        post.content, post.title, post.excerpt
                    )
                    recent_quality_scores.append(quality['overall_score'])
                except:
                    pass
            
            if recent_quality_scores:
                recent_average = sum(recent_quality_scores) / len(recent_quality_scores)
                if recent_average >= 80:
                    self.stdout.write(f"   ✅ Recent Quality: {recent_average:.1f} (last 30 days)")
                    criteria_met += 1
                else:
                    self.stdout.write(f"   ❌ Recent Quality: {recent_average:.1f} (last 30 days)")
            else:
                self.stdout.write(f"   ⚠️ Recent Quality: Unable to assess")
        else:
            self.stdout.write(f"   ⚠️ Recent Quality: No recent posts")
        
        # Overall assessment
        readiness_score = (criteria_met / total_criteria) * 100
        
        self.stdout.write(f"\n   📈 OVERALL READINESS: {readiness_score:.0f}% ({criteria_met}/{total_criteria} criteria met)")
        
        if readiness_score >= 75:
            self.stdout.write("   🎉 GOOD: Site appears ready for AdSense application!")
        elif readiness_score >= 50:
            self.stdout.write("   ⚠️ MODERATE: Some improvements needed before AdSense application")
        else:
            self.stdout.write("   ❌ POOR: Significant improvements needed for AdSense compliance")

    def _provide_recommendations(self, audit_results):
        """Provide actionable recommendations"""
        recommendations = []
        
        total_posts = audit_results['total_posts']
        poor_posts = len(audit_results['poor_posts'])
        average_score = audit_results['average_score']
        
        # Content quantity recommendations
        if total_posts < 20:
            needed = 20 - total_posts
            recommendations.append(f"📝 Create {needed} more high-quality posts (current: {total_posts})")
        
        # Content quality recommendations
        if poor_posts > 0:
            recommendations.append(f"🔧 Regenerate {poor_posts} low-quality posts using CRAG")
        
        if average_score < 80:
            recommendations.append(f"📈 Improve overall content quality (current average: {average_score:.1f})")
        
        # Technical recommendations
        recommendations.extend([
            "🚀 Use CRAG content generation for all new posts",
            "📊 Monitor quality scores regularly using AdSense quality checker",
            "🔄 Set up automated quality monitoring and alerts",
            "📱 Ensure all content is mobile-friendly and fast-loading",
            "🔗 Add relevant internal and external links to posts",
            "🖼️ Include high-quality, relevant images in all posts",
            "📋 Create comprehensive privacy policy and terms of service",
            "🎯 Focus on user experience and engagement metrics"
        ])
        
        self.stdout.write("   💡 RECOMMENDED ACTIONS:")
        for i, rec in enumerate(recommendations[:8], 1):
            self.stdout.write(f"   {i}. {rec}")
        
        # Next steps
        self.stdout.write(f"\n   🎯 IMMEDIATE NEXT STEPS:")
        self.stdout.write(f"   1. Run: python manage.py generate_crag_content --count 5")
        self.stdout.write(f"   2. Review and publish regenerated draft posts")
        self.stdout.write(f"   3. Monitor quality scores for new content")
        self.stdout.write(f"   4. Apply for AdSense when readiness score > 75%")