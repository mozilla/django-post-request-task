import os
from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()


setup(
    name='django-post-request-task',
    version='0.0.2',
    description='A celery task class whose execution is delayed until after '
                'the request finishes',
    author='Mathieu Pillard',
    author_email='mpillard@mozilla.com',
    url='http://github.com/mozilla/django-post-request-task',
    license='MIT',
    long_description=README,
    packages=['post_request_task'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Environment :: Web Environment :: Mozilla',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
