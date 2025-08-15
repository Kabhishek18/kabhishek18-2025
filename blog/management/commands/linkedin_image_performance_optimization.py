"""
LinkedIn Image Performance Optimization Command

This management command provides performance optimization and validation
for the LinkedIn image integration system.

Usage:
    python manage.py linkedin_image_performance_optimization [options]

Requirements covered: 1.4, 3.4, 3.5
"""

import os
import time
import tempfile
import shutil
import statistics
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import psutil

try:
    from blog.models import Post, Category, Tag
    from blog.services.linkedin_image_service import LinkedInImageService
    from blog.services.linkedin_content_formatter import LinkedInContentFormatter
    from blog.utils.image_processor import ImageProcessor, ImageProcessingError
    from blog.linkedin_models import LinkedInConfig, LinkedInPost
except ImportError as e:
    print(f"Import error: {e}")


class Command(BaseCommand):
    help = 'Optimize and validate LinkedIn image integration performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--benchmark',
            action='store_true',
            help='Run performance benchmarks'
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate image processing quality'
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help='Run optimization recommendations'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all optimization tasks'
        )
        parser.add_argument(
            '--iterations',
            type=int,
            default=3,
            help='Number of benchmark iterations (default: 3)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(
            self.style.SUCCESS('LinkedIn Image Performance Optimization Tool')
        )
        self.stdout.write('=' * 60)
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        try:
            # Create test images
            self.test_images = self._create_test_images()
            
            # Run requested operations
            if options['all'] or options['benchmark']:
                self._run_benchmarks(options['iterations'])
            
            if options['all'] or options['validate']:
                self._validate_quality()
            
            if options['all'] or options['optimize']:
                self._provide_optimization_recommendations()
            
            if not any([options['benchmark'], options['validate'], options['optimize'], options['all']]):
                self.stdout.write(
                    self.style.WARNING('No operation specified. Use --help for options.')
                )
        
        finally:
            # Cleanup temporary directory
            shutil.rmtree(self.temp_dir)
        
        self.stdout.write(
            self.style.SUCCESS('\nOptimization analysis complete!')
        )
    
    def _create_test_images(self):
        """Create test images for performance testing."""
        self.stdout.write('Creating test images...')
        
        images = {}
        
        # Test image specifications
        test_specs = [
            ('small', (800, 600), 'Small image test'),
            ('medium', (1920, 1080), 'Medium resolution test'),
            ('large', (3840, 2160), 'Large 4K image test'),
            ('linkedin_perfect', (1200, 627), 'Perfect LinkedIn dimensions'),
            ('square', (1080, 1080), 'Square aspect ratio'),
            ('portrait', (800, 1200), 'Portrait orientation')
        ]
        
        for name, (width, height), description in test_specs:
            # Create image with gradient pattern for realistic file size
            img = Image.new('RGB', (width, height))
            pixels = img.load()
            
            for x in range(width):
                for y in range(height):
                    r = int((x / width) * 255)
                    g = int((y / height) * 255)
                    b = int(((x + y) / (width + height)) * 255)
                    pixels[x, y] = (r, g, b)
            
            path = os.path.join(self.temp_dir, f'{name}.jpg')
            img.save(path, 'JPEG', quality=85, optimize=True)
            images[name] = {
                'path': path,
                'description': description,
                'dimensions': (width, height),
                'size': os.path.getsize(path)
            }
        
        self.stdout.write(f'Created {len(images)} test images')
        return images
    
    def _run_benchmarks(self, iterations):
        """Run performance benchmarks."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('PERFORMANCE BENCHMARKS'))
        self.stdout.write('=' * 60)
        
        processor = ImageProcessor()
        image_service = LinkedInImageService()
        
        benchmark_results = {}
        
        for image_name, image_info in self.test_images.items():
            self.stdout.write(f'\nBenchmarking: {image_info["description"]}')
            self.stdout.write(f'Dimensions: {image_info["dimensions"]}')
            self.stdout.write(f'File Size: {image_info["size"] / 1024:.1f} KB')
            
            # Run multiple iterations
            processing_times = []
            memory_usage = []
            
            for i in range(iterations):
                # Monitor memory usage
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                
                # Time the processing
                start_time = time.time()
                
                try:
                    output_path = os.path.join(self.temp_dir, f'processed_{image_name}_{i}.jpg')
                    processed_path = processor.process_for_linkedin(
                        image_info['path'], 
                        output_path
                    )
                    
                    processing_time = time.time() - start_time
                    processing_times.append(processing_time)
                    
                    # Memory after processing
                    memory_after = process.memory_info().rss / 1024 / 1024
                    memory_increase = memory_after - memory_before
                    memory_usage.append(memory_increase)
                    
                    # Validate output
                    is_compatible, issues = processor.is_linkedin_compatible(processed_path)
                    
                    self.stdout.write(
                        f'  Iteration {i+1}: {processing_time:.2f}s, '
                        f'Memory: +{memory_increase:.1f}MB, '
                        f'Compatible: {is_compatible}'
                    )
                
                except ImageProcessingError as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Iteration {i+1}: FAILED - {e}')
                    )
                    processing_times.append(None)
                    memory_usage.append(0)
            
            # Calculate statistics
            valid_times = [t for t in processing_times if t is not None]
            if valid_times:
                avg_time = statistics.mean(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                avg_memory = statistics.mean(memory_usage)
                
                benchmark_results[image_name] = {
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'avg_memory': avg_memory,
                    'success_rate': len(valid_times) / iterations * 100,
                    'dimensions': image_info['dimensions'],
                    'file_size': image_info['size']
                }
                
                # Performance assessment
                performance_rating = self._assess_performance(avg_time, image_info['dimensions'])
                
                self.stdout.write(
                    f'  Results: avg={avg_time:.2f}s, min={min_time:.2f}s, '
                    f'max={max_time:.2f}s, memory={avg_memory:.1f}MB'
                )
                self.stdout.write(
                    f'  Performance: {performance_rating}'
                )
        
        # Summary report
        self._print_benchmark_summary(benchmark_results)
    
    def _assess_performance(self, processing_time, dimensions):
        """Assess performance rating based on processing time and image size."""
        width, height = dimensions
        pixel_count = width * height
        
        # Performance thresholds based on image size
        if pixel_count < 1000000:  # < 1MP
            if processing_time < 1.0:
                return self.style.SUCCESS('EXCELLENT')
            elif processing_time < 2.0:
                return self.style.SUCCESS('GOOD')
            elif processing_time < 5.0:
                return self.style.WARNING('ACCEPTABLE')
            else:
                return self.style.ERROR('POOR')
        
        elif pixel_count < 5000000:  # < 5MP
            if processing_time < 3.0:
                return self.style.SUCCESS('EXCELLENT')
            elif processing_time < 7.0:
                return self.style.SUCCESS('GOOD')
            elif processing_time < 15.0:
                return self.style.WARNING('ACCEPTABLE')
            else:
                return self.style.ERROR('POOR')
        
        else:  # >= 5MP
            if processing_time < 10.0:
                return self.style.SUCCESS('EXCELLENT')
            elif processing_time < 20.0:
                return self.style.SUCCESS('GOOD')
            elif processing_time < 30.0:
                return self.style.WARNING('ACCEPTABLE')
            else:
                return self.style.ERROR('POOR')
    
    def _print_benchmark_summary(self, results):
        """Print benchmark summary report."""
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write(self.style.SUCCESS('BENCHMARK SUMMARY'))
        self.stdout.write('-' * 60)
        
        if not results:
            self.stdout.write(self.style.ERROR('No successful benchmarks to report'))
            return
        
        # Overall statistics
        all_times = [r['avg_time'] for r in results.values()]
        all_memory = [r['avg_memory'] for r in results.values()]
        
        overall_avg_time = statistics.mean(all_times)
        overall_avg_memory = statistics.mean(all_memory)
        
        self.stdout.write(f'Overall Average Processing Time: {overall_avg_time:.2f}s')
        self.stdout.write(f'Overall Average Memory Usage: {overall_avg_memory:.1f}MB')
        
        # Best and worst performers
        best_performer = min(results.items(), key=lambda x: x[1]['avg_time'])
        worst_performer = max(results.items(), key=lambda x: x[1]['avg_time'])
        
        self.stdout.write(f'\nBest Performer: {best_performer[0]} ({best_performer[1]["avg_time"]:.2f}s)')
        self.stdout.write(f'Worst Performer: {worst_performer[0]} ({worst_performer[1]["avg_time"]:.2f}s)')
        
        # Performance recommendations
        if overall_avg_time > 10.0:
            self.stdout.write(
                self.style.WARNING('\nWARNING: Average processing time is high (>10s)')
            )
            self.stdout.write('Consider optimizing image processing pipeline')
        
        if overall_avg_memory > 200.0:
            self.stdout.write(
                self.style.WARNING('\nWARNING: High memory usage detected (>200MB)')
            )
            self.stdout.write('Consider implementing memory optimization')
    
    def _validate_quality(self):
        """Validate image processing quality."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('QUALITY VALIDATION'))
        self.stdout.write('=' * 60)
        
        processor = ImageProcessor()
        quality_results = {}
        
        for image_name, image_info in self.test_images.items():
            self.stdout.write(f'\nValidating: {image_info["description"]}')
            
            try:
                output_path = os.path.join(self.temp_dir, f'quality_{image_name}.jpg')
                processed_path = processor.process_for_linkedin(
                    image_info['path'], 
                    output_path
                )
                
                # Validate LinkedIn compatibility
                is_compatible, issues = processor.is_linkedin_compatible(processed_path)
                
                # Get processed image info
                with Image.open(processed_path) as img:
                    processed_dimensions = img.size
                    processed_format = img.format
                    processed_mode = img.mode
                
                processed_size = os.path.getsize(processed_path)
                size_reduction = (image_info['size'] - processed_size) / image_info['size'] * 100
                
                quality_results[image_name] = {
                    'compatible': is_compatible,
                    'issues': issues,
                    'original_dimensions': image_info['dimensions'],
                    'processed_dimensions': processed_dimensions,
                    'original_size': image_info['size'],
                    'processed_size': processed_size,
                    'size_reduction': size_reduction,
                    'format': processed_format,
                    'mode': processed_mode
                }
                
                # Report results
                self.stdout.write(f'  LinkedIn Compatible: {is_compatible}')
                if issues:
                    for issue in issues:
                        self.stdout.write(f'    Issue: {issue}')
                
                self.stdout.write(f'  Dimensions: {image_info["dimensions"]} -> {processed_dimensions}')
                self.stdout.write(f'  File Size: {image_info["size"]/1024:.1f}KB -> {processed_size/1024:.1f}KB ({size_reduction:+.1f}%)')
                self.stdout.write(f'  Format: {processed_format}, Mode: {processed_mode}')
                
                if is_compatible:
                    self.stdout.write(self.style.SUCCESS('  ✓ PASSED'))
                else:
                    self.stdout.write(self.style.ERROR('  ✗ FAILED'))
            
            except ImageProcessingError as e:
                quality_results[image_name] = {
                    'compatible': False,
                    'error': str(e)
                }
                self.stdout.write(self.style.ERROR(f'  Processing Error: {e}'))
        
        # Quality summary
        self._print_quality_summary(quality_results)
    
    def _print_quality_summary(self, results):
        """Print quality validation summary."""
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write(self.style.SUCCESS('QUALITY SUMMARY'))
        self.stdout.write('-' * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('compatible', False))
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        self.stdout.write(f'Total Tests: {total_tests}')
        self.stdout.write(f'Passed: {passed_tests}')
        self.stdout.write(f'Success Rate: {success_rate:.1f}%')
        
        if success_rate >= 90:
            self.stdout.write(self.style.SUCCESS('✓ EXCELLENT quality validation'))
        elif success_rate >= 75:
            self.stdout.write(self.style.SUCCESS('✓ GOOD quality validation'))
        elif success_rate >= 50:
            self.stdout.write(self.style.WARNING('⚠ ACCEPTABLE quality validation'))
        else:
            self.stdout.write(self.style.ERROR('✗ POOR quality validation'))
        
        # Failed tests details
        failed_tests = [name for name, result in results.items() if not result.get('compatible', False)]
        if failed_tests:
            self.stdout.write(f'\nFailed Tests: {", ".join(failed_tests)}')
    
    def _provide_optimization_recommendations(self):
        """Provide optimization recommendations."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('OPTIMIZATION RECOMMENDATIONS'))
        self.stdout.write('=' * 60)
        
        recommendations = []
        
        # Check Django settings
        if hasattr(settings, 'LINKEDIN_IMAGE_SETTINGS'):
            linkedin_settings = settings.LINKEDIN_IMAGE_SETTINGS
            
            if linkedin_settings.get('IMAGE_QUALITY', 85) > 90:
                recommendations.append({
                    'type': 'settings',
                    'priority': 'medium',
                    'message': 'Consider reducing IMAGE_QUALITY setting to 85 for better performance'
                })
            
            if not linkedin_settings.get('CACHE_PROCESSED_IMAGES', False):
                recommendations.append({
                    'type': 'settings',
                    'priority': 'high',
                    'message': 'Enable CACHE_PROCESSED_IMAGES for better performance'
                })
        else:
            recommendations.append({
                'type': 'settings',
                'priority': 'high',
                'message': 'Add LINKEDIN_IMAGE_SETTINGS to Django settings for optimization'
            })
        
        # Check system resources
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            
            if memory.available < 1024 * 1024 * 1024:  # Less than 1GB available
                recommendations.append({
                    'type': 'system',
                    'priority': 'high',
                    'message': f'Low available memory ({memory.available/1024/1024/1024:.1f}GB). Consider increasing system memory.'
                })
            
            if cpu_count < 2:
                recommendations.append({
                    'type': 'system',
                    'priority': 'medium',
                    'message': 'Single CPU core detected. Multi-core system recommended for better performance.'
                })
        
        except ImportError:
            recommendations.append({
                'type': 'dependency',
                'priority': 'low',
                'message': 'Install psutil for system monitoring: pip install psutil'
            })
        
        # Check image processing configuration
        recommendations.extend([
            {
                'type': 'optimization',
                'priority': 'medium',
                'message': 'Consider implementing async image processing for better user experience'
            },
            {
                'type': 'optimization',
                'priority': 'low',
                'message': 'Implement image preprocessing during upload to reduce posting time'
            },
            {
                'type': 'monitoring',
                'priority': 'medium',
                'message': 'Set up monitoring for image processing performance metrics'
            }
        ])
        
        # Print recommendations by priority
        for priority in ['high', 'medium', 'low']:
            priority_recs = [r for r in recommendations if r['priority'] == priority]
            if priority_recs:
                self.stdout.write(f'\n{priority.upper()} PRIORITY:')
                for rec in priority_recs:
                    icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
                    self.stdout.write(f'  {icon} [{rec["type"].upper()}] {rec["message"]}')
        
        if not recommendations:
            self.stdout.write(self.style.SUCCESS('✓ No optimization recommendations at this time'))
        
        # Configuration example
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('RECOMMENDED CONFIGURATION:')
        self.stdout.write('-' * 60)
        
        config_example = '''
# Add to settings.py
LINKEDIN_IMAGE_SETTINGS = {
    'ENABLE_IMAGE_UPLOAD': True,
    'MAX_IMAGES_PER_POST': 1,
    'IMAGE_QUALITY': 85,
    'RESIZE_LARGE_IMAGES': True,
    'FALLBACK_TO_TEXT_ONLY': True,
    'CACHE_PROCESSED_IMAGES': True,
    'MAX_PROCESSING_TIME': 30,  # seconds
    'ASYNC_PROCESSING': True,
}

# For production environments
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
        '''
        
        self.stdout.write(config_example)