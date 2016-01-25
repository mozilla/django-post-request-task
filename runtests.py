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

failures = DiscoverRunner(verbosity=1).run_tests(['post_request_task'])
if failures:
    sys.exit(failures)
