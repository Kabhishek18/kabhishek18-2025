#!/usr/bin/env python
"""
Simple test runner for schema service tests.
This script can be used to run the schema service tests independently.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kabhishek18.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run only the schema service tests
    failures = test_runner.run_tests(["blog.tests_schema_service"])
    
    if failures:
        sys.exit(1)
    else:
        print("All schema service tests passed!")
        sys.exit(0)