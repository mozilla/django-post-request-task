#!/usr/bin/env python
import sys
import django
from django.conf import settings


settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    INSTALLED_APPS=()
)
django.setup()


from django.test.runner import DiscoverRunner

if len(sys.argv) > 1:
    target = sys.argv[1:]
else:
    target = ['post_request_task']

failures = DiscoverRunner(verbosity=1).run_tests(target)
if failures:
    sys.exit(failures)
