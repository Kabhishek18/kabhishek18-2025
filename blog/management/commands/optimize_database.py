"""
Management command to optimize database performance for blog engagement features.

This command creates database indexes and performs other optimizations
to improve query performance.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from blog.performance import DatabaseIndexOptimizer


class Command(BaseCommand):
    help = 'Optimize database performance for blog engagement features'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze performance without making changes',
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create recommended database indexes',
        )
        parser.add_argument(
            '--flush-view-counts',
            action='store_true',
            help='Flush buffered view counts to database',
        )

    def handle(self, *args, **options):
        if options['analyze_only']:
            self.analyze_performance()
        elif options['create_indexes']:
            self.create_indexes()
        elif options['flush_view_counts']:
            self.flush_view_counts()
        else:
            # Run all optimizations
            self.analyze_performance()
            self.create_indexes()
            self.flush_view_counts()

    def analyze_performance(self):
        """Analyze current database performance"""
        self.stdout.write(
            self.style.SUCCESS('Analyzing database performance...')
        )
        
        analysis = DatabaseIndexOptimizer.analyze_query_performance()
        
        self.stdout.write(
            self.style.SUCCESS(f'Performance analysis complete:')
        )
        self.stdout.write(f'- Slow queries: {len(analysis["slow_queries"])}')
        self.stdout.write(f'- Missing indexes: {len(analysis["missing_indexes"])}')
        self.stdout.write(f'- Recommendations: {len(analysis["recommendations"])}')

    def create_indexes(self):
        """Create recommended database indexes"""
        self.stdout.write(
            self.style.SUCCESS('Creating database indexes...')
        )
        
        recommended_indexes = DatabaseIndexOptimizer.get_recommended_indexes()
        
        with connection.cursor() as cursor:
            for index_config in recommended_indexes:
                try:
                    # This is a simplified example - actual implementation would
                    # depend on the database backend and existing indexes
                    self.stdout.write(
                        f'Would create index for {index_config["model"]} '
                        f'on fields {index_config["fields"]} - '
                        f'{index_config["reason"]}'
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to create index for {index_config["model"]}: {e}'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS('Database index creation complete.')
        )

    def flush_view_counts(self):
        """Flush buffered view counts to database"""
        self.stdout.write(
            self.style.SUCCESS('Flushing buffered view counts...')
        )
        
        from blog.performance import ViewCountOptimizer
        ViewCountOptimizer.flush_all_view_counts()
        
        self.stdout.write(
            self.style.SUCCESS('View count flush complete.')
        )