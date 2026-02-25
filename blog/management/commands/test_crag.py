"""
Test CRAG System

This command tests the CRAG (Corrective Retrieval-Augmented Generation) system
to ensure it's working correctly and producing high-quality content.
"""

import time
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from blog.services.crag_service import CRAGService
from blog.services.adsense_quality_checker import AdSenseQualityChecker

User = get_user_model()


class Command(BaseCommand):
    help = 'Test CRAG system functionality and quality output'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run quick test without full content generation'
        )
        parser.add_argument(
            '--topic',
            type=str,
            default='Advanced Python Performance Optimization',
            help='Topic to test content generation'
        )

    def handle(self, *args, **options):
        self.quick = options['quick']
        self.topic = options['topic']
        
        self.stdout.write(self.style.SUCCESS("🧪 Testing CRAG System"))
        self.stdout.write("=" * 50)
        
        # Test 1: Service Initialization
        self.test_service_initialization()
        
        # Test 2: Quality Checker
        self.test_quality_checker()
        
        if not self.quick:
            # Test 3: Content Generation
            self.test_content_generation()
            
            # Test 4: Quality Assessment
            self.test_quality_assessment()
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("✅ All tests completed!"))

    def test_service_initialization(self):
        """Test CRAG service initialization"""
        self.stdout.write("\n🔧 Test 1: Service Initialization")
        
        try:
            crag_service = CRAGService()
            self.stdout.write("   ✅ CRAG Service initialized successfully")
            
            # Test configuration
            self.stdout.write(f"   📊 Min Quality Score: {crag_service.min_quality_score}")
            self.stdout.write(f"   📝 Min Word Count: {crag_service.min_word_count}")
            self.stdout.write(f"   🔄 Max Retries: {crag_service.max_retries}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ CRAG Service initialization failed: {e}"))
            raise CommandError("CRAG service initialization failed")

    def test_quality_checker(self):
        """Test AdSense quality checker"""
        self.stdout.write("\n📊 Test 2: Quality Checker")
        
        try:
            checker = AdSenseQualityChecker()
            self.stdout.write("   ✅ AdSense Quality Checker initialized successfully")
            
            # Test with sample content
            sample_content = """
            <h2>Introduction to Advanced Python Optimization</h2>
            <p>Python performance optimization is crucial for building scalable applications. This comprehensive guide explores advanced techniques that experienced developers use to maximize Python performance.</p>
            
            <h2>Memory Management Techniques</h2>
            <p>Effective memory management is fundamental to Python optimization. Understanding how Python handles memory allocation can lead to significant performance improvements.</p>
            
            <h3>Object Pooling</h3>
            <ul>
                <li>Reuse objects instead of creating new ones</li>
                <li>Reduce garbage collection overhead</li>
                <li>Implement custom pool managers for frequently used objects</li>
            </ul>
            
            <h2>Algorithm Optimization</h2>
            <p>Choosing the right algorithms and data structures is essential for optimal performance.</p>
            
            <h3>Time Complexity Analysis</h3>
            <p>Understanding Big O notation helps in selecting efficient algorithms.</p>
            
            <pre><code>
# Example: Efficient list comprehension
result = [x*2 for x in range(1000) if x % 2 == 0]

# Instead of:
result = []
for x in range(1000):
    if x % 2 == 0:
        result.append(x*2)
            </code></pre>
            
            <h2>Profiling and Benchmarking</h2>
            <p>Regular profiling helps identify performance bottlenecks in your Python applications.</p>
            
            <h2>Conclusion</h2>
            <p>Implementing these advanced optimization techniques will significantly improve your Python application performance.</p>
            """
            
            sample_title = "Advanced Python Performance Optimization Techniques"
            sample_excerpt = "Learn advanced Python optimization techniques including memory management, algorithm selection, and profiling strategies for building high-performance applications."
            
            report = checker.comprehensive_quality_assessment(
                sample_content, sample_title, sample_excerpt
            )
            
            self.stdout.write(f"   📊 Sample Content Quality Score: {report['overall_score']:.1f}/100")
            self.stdout.write(f"   🎯 AdSense Ready: {report['adsense_ready']}")
            self.stdout.write(f"   📝 Category: {report['category']}")
            
            if report['issues']:
                self.stdout.write("   ⚠️ Issues found:")
                for issue in report['issues'][:3]:
                    self.stdout.write(f"      - {issue}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Quality checker test failed: {e}"))

    def test_content_generation(self):
        """Test content generation"""
        self.stdout.write(f"\n🤖 Test 3: Content Generation")
        self.stdout.write(f"   Topic: {self.topic}")
        
        try:
            crag_service = CRAGService()
            
            self.stdout.write("   🔍 Starting content generation...")
            start_time = time.time()
            
            content_data = crag_service.generate_high_quality_content(
                topic=self.topic,
                target_audience="senior developers"
            )
            
            generation_time = time.time() - start_time
            
            if content_data:
                self.stdout.write(f"   ✅ Content generated successfully in {generation_time:.1f}s")
                self.stdout.write(f"   📝 Title: {content_data['title']}")
                self.stdout.write(f"   📊 Word Count: {len(content_data['content'].split())} words")
                self.stdout.write(f"   🏷️ Category: {content_data['category']}")
                self.stdout.write(f"   🔖 Tags: {', '.join(content_data['tags'])}")
                
                # Store for quality assessment
                self.generated_content = content_data
                
            else:
                self.stdout.write(self.style.ERROR("   ❌ Content generation failed"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Content generation test failed: {e}"))

    def test_quality_assessment(self):
        """Test quality assessment of generated content"""
        self.stdout.write("\n📈 Test 4: Quality Assessment")
        
        if not hasattr(self, 'generated_content'):
            self.stdout.write("   ⚠️ No generated content to assess")
            return
        
        try:
            checker = AdSenseQualityChecker()
            content_data = self.generated_content
            
            self.stdout.write("   🔍 Assessing generated content quality...")
            
            report = checker.comprehensive_quality_assessment(
                content_data['content'],
                content_data['title'],
                content_data['excerpt']
            )
            
            self.stdout.write(f"   📊 QUALITY RESULTS:")
            self.stdout.write(f"      Overall Score: {report['overall_score']:.1f}/100")
            self.stdout.write(f"      Category: {report['category']}")
            self.stdout.write(f"      AdSense Ready: {report['adsense_ready']}")
            
            # Detailed metrics
            metrics = report.get('metrics', {})
            
            if 'content' in metrics:
                content_metrics = metrics['content']
                self.stdout.write(f"      Word Count: {content_metrics.get('word_count', 0)}")
                self.stdout.write(f"      Content Score: {content_metrics.get('word_score', 0):.1f}")
            
            if 'readability' in metrics:
                readability = metrics['readability']
                self.stdout.write(f"      Readability: {readability.get('flesch_score', 0):.1f}")
            
            if 'structure' in metrics:
                structure = metrics['structure']
                self.stdout.write(f"      Structure Score: {structure.get('structure_score', 0):.1f}")
            
            # Issues and recommendations
            if report['issues']:
                self.stdout.write(f"   ⚠️ ISSUES ({len(report['issues'])}):")
                for issue in report['issues'][:3]:
                    self.stdout.write(f"      - {issue}")
            
            if report['recommendations']:
                self.stdout.write(f"   💡 RECOMMENDATIONS ({len(report['recommendations'])}):")
                for rec in report['recommendations'][:3]:
                    self.stdout.write(f"      - {rec}")
            
            # Overall assessment
            if report['overall_score'] >= 85:
                self.stdout.write("   🎉 EXCELLENT: Content meets high-quality standards!")
            elif report['overall_score'] >= 70:
                self.stdout.write("   ✅ GOOD: Content meets basic quality requirements")
            else:
                self.stdout.write("   ⚠️ NEEDS IMPROVEMENT: Content below quality threshold")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Quality assessment test failed: {e}"))