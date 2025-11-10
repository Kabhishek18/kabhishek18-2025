"""
Management command to audit content for AdSense compliance
"""

from django.core.management.base import BaseCommand
from blog.models import Post
from blog.content_quality import generate_quality_report
from django.utils.html import strip_tags


class Command(BaseCommand):
    help = 'Audit blog content for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically unpublish low-quality posts'
        )
        parser.add_argument(
            '--min-words',
            type=int,
            default=300,
            help='Minimum word count (default: 300)'
        )
        parser.add_argument(
            '--min-score',
            type=int,
            default=70,
            help='Minimum quality score (default: 70)'
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        min_words = options['min_words']
        min_score = options['min_score']

        self.stdout.write("\n" + "="*80)
        self.stdout.write("🔍 AdSense Content Audit")
        self.stdout.write("="*80 + "\n")

        # Get all published posts
        posts = Post.objects.filter(status='published').order_by('-created_at')
        
        if not posts.exists():
            self.stdout.write(self.style.WARNING('No published posts found.'))
            return

        # Analyze posts
        thin_content = []
        low_quality = []
        good_quality = []
        excellent_quality = []

        self.stdout.write(f"Analyzing {posts.count()} published posts...\n")

        for post in posts:
            # Get word count
            plain_text = strip_tags(post.content)
            words = len(plain_text.split())
            
            # Get quality score
            try:
                report = generate_quality_report(post.content, post.title, post.excerpt)
                score = report['score']
            except Exception:
                score = 0

            post_info = {
                'id': post.id,
                'title': post.title,
                'words': words,
                'score': score,
                'url': f'/blog/{post.slug}/'
            }

            # Categorize
            if words < min_words:
                thin_content.append(post_info)
            elif score < min_score:
                low_quality.append(post_info)
            elif score >= 90:
                excellent_quality.append(post_info)
            else:
                good_quality.append(post_info)

        # Display results
        self.stdout.write("\n" + "="*80)
        self.stdout.write("📊 AUDIT RESULTS")
        self.stdout.write("="*80 + "\n")

        # Summary
        total = posts.count()
        issues = len(thin_content) + len(low_quality)
        
        self.stdout.write(f"Total Posts: {total}")
        self.stdout.write(f"✅ Excellent (90+): {len(excellent_quality)}")
        self.stdout.write(f"✅ Good (70-89): {len(good_quality)}")
        self.stdout.write(f"⚠️  Low Quality (<70): {len(low_quality)}")
        self.stdout.write(f"❌ Thin Content (<{min_words} words): {len(thin_content)}")
        self.stdout.write(f"\n🚨 Issues Found: {issues}\n")

        # Thin content details
        if thin_content:
            self.stdout.write("\n" + "-"*80)
            self.stdout.write("❌ THIN CONTENT (Must Fix!)")
            self.stdout.write("-"*80)
            for post in thin_content:
                self.stdout.write(
                    f"\nID: {post['id']} | Words: {post['words']} | Score: {post['score']:.0f}"
                )
                self.stdout.write(f"Title: {post['title']}")
                self.stdout.write(f"URL: {post['url']}")
                
                if fix_mode:
                    # Unpublish
                    Post.objects.filter(id=post['id']).update(status='draft')
                    self.stdout.write(self.style.WARNING("→ Unpublished (saved as draft)"))

        # Low quality details
        if low_quality:
            self.stdout.write("\n" + "-"*80)
            self.stdout.write("⚠️  LOW QUALITY CONTENT (Should Improve)")
            self.stdout.write("-"*80)
            for post in low_quality[:10]:  # Show first 10
                self.stdout.write(
                    f"\nID: {post['id']} | Words: {post['words']} | Score: {post['score']:.0f}"
                )
                self.stdout.write(f"Title: {post['title']}")
                
                if fix_mode:
                    # Unpublish
                    Post.objects.filter(id=post['id']).update(status='draft')
                    self.stdout.write(self.style.WARNING("→ Unpublished (saved as draft)"))
            
            if len(low_quality) > 10:
                self.stdout.write(f"\n... and {len(low_quality) - 10} more")

        # Excellent content
        if excellent_quality:
            self.stdout.write("\n" + "-"*80)
            self.stdout.write("🌟 EXCELLENT CONTENT (Keep These!)")
            self.stdout.write("-"*80)
            for post in excellent_quality[:5]:  # Show first 5
                self.stdout.write(
                    f"\nID: {post['id']} | Words: {post['words']} | Score: {post['score']:.0f}"
                )
                self.stdout.write(f"Title: {post['title']}")

        # Recommendations
        self.stdout.write("\n" + "="*80)
        self.stdout.write("💡 RECOMMENDATIONS FOR ADSENSE APPROVAL")
        self.stdout.write("="*80 + "\n")

        if thin_content:
            self.stdout.write(f"1. ❌ Delete or improve {len(thin_content)} thin content posts")
            self.stdout.write(f"   → Each post needs {min_words}+ words")
            if fix_mode:
                self.stdout.write(f"   ✅ Unpublished automatically")
            else:
                self.stdout.write(f"   Run with --fix to unpublish automatically")

        if low_quality:
            self.stdout.write(f"\n2. ⚠️  Improve {len(low_quality)} low-quality posts")
            self.stdout.write(f"   → Use regeneration or manual editing")
            self.stdout.write(f"   → Target quality score: 90+")
            if fix_mode:
                self.stdout.write(f"   ✅ Unpublished automatically")

        if len(excellent_quality) + len(good_quality) < 20:
            needed = 20 - (len(excellent_quality) + len(good_quality))
            self.stdout.write(f"\n3. 📝 Create {needed} more high-quality posts")
            self.stdout.write(f"   → AdSense wants 20-30 quality posts")
            self.stdout.write(f"   → Use: python manage.py auto_publish_content --count {needed} --quality expert")

        self.stdout.write("\n4. ✅ Manually review ALL AI-generated content")
        self.stdout.write("   → Add personal insights and examples")
        self.stdout.write("   → Make content unique and valuable")

        self.stdout.write("\n5. 📄 Add required pages:")
        self.stdout.write("   → About Us (300+ words)")
        self.stdout.write("   → Contact page")
        self.stdout.write("   → Privacy Policy")
        self.stdout.write("   → Terms of Service")

        self.stdout.write("\n6. ⏰ Publish gradually:")
        self.stdout.write("   → 2-3 posts per week")
        self.stdout.write("   → Wait 2-4 weeks before applying")

        # Final summary
        self.stdout.write("\n" + "="*80)
        if issues == 0:
            self.stdout.write(self.style.SUCCESS("✅ No critical issues found!"))
            self.stdout.write("Your content meets basic AdSense requirements.")
            self.stdout.write("\nNext steps:")
            self.stdout.write("1. Manually review all posts")
            self.stdout.write("2. Add personal insights")
            self.stdout.write("3. Add required pages")
            self.stdout.write("4. Wait 2-4 weeks")
            self.stdout.write("5. Apply to AdSense")
        else:
            self.stdout.write(self.style.ERROR(f"🚨 {issues} issues found that must be fixed!"))
            if fix_mode:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Problematic posts have been unpublished."))
                self.stdout.write("Review and improve them before republishing.")
            else:
                self.stdout.write(f"\nRun with --fix to automatically unpublish problematic posts:")
                self.stdout.write(f"python manage.py adsense_audit --fix")

        self.stdout.write("="*80 + "\n")
