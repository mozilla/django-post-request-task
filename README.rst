django-post-request-task
========================

.. image:: https://travis-ci.org/mozilla/django-post-request-task.svg?branch=master
    :target: https://travis-ci.org/mozilla/django-post-request-task

A celery task class whose execution is delayed until after the request
finishes, using request_started and request_finished signals from django and
thread locals.

This is useful if your views are wrapped in transactions (as they should if
you're making database modifications in them), as you can end up triggering a
celery task too soon before the transaction has been committed (or even trigger
a task when the corresponding transaction has been rolled back).

By listening to the request_started and request_finished django signals, we can
safely trigger a task after all transactions created from @atomic or
ATOMIC_REQUESTS have been committed.

Usage
-----

.. code-block::

    from celery import Celery
    from post_request_task.task import PostRequestTask


    app = Celery('myapp', task_cls=PostRequestTask)

    @app.task
    def my_task():
        # If .delay() is called on this task inside a django request-response
        # cycle it will be called once the request is finished, and not before.
        pass


Or, if you are using the task decorator directly:

.. code-block::

    from post_request_task.task import task

    @task
    def my_task():
        pass


That's it. If the task is called from outside the django request-response
cycle, then it will be triggered normally.


Running tests
-------------

.. code-block::

    $ make testenv
    $ make test

Tests are run with Django 1.8.x by default. If you want to override this, use:


.. code-block::

    $ DJANGO="Django==1.9" make testenv
    $ make test
