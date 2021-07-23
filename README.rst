django-post-request-task
========================

.. image:: https://circleci.com/gh/mozilla/django-post-request-task.svg?style=svg
    :target: https://circleci.com/gh/mozilla/django-post-request-task

A celery task class whose execution is delayed until after the request
finishes, using ``request_started`` and ``request_finished`` signals from django
and thread locals.

This is useful if your views are wrapped in transactions (as they should if
you're making database modifications in them), as you can end up triggering a
celery task too soon before the transaction has been committed (or even trigger
a task when the corresponding transaction has been rolled back).

By listening to the `request_started` and `request_finished` django signals, we
can safely trigger a task after all transactions created from ``@atomic`` or
``ATOMIC_REQUESTS`` have been committed.

Usage
-----

.. code-block:: python

    from celery import Celery
    from post_request_task.task import PostRequestTask


    app = Celery('myapp', task_cls=PostRequestTask)

    @app.task
    def my_task():
        # If .delay() is called on this task inside a django request-response
        # cycle it will be called once the request is finished, and not before.
        pass


Or, if you are using the decorator directly:

.. code-block:: python

    from post_request_task.task import shared_task

    @shared_task
    def my_task():
        pass


That's it. If the task is called from outside the django request-response
cycle, then it will be triggered normally.

As a bonus feature, if the same task is called with the same argument several
times during a request-response cycle, it will only be queued up once.


Running tests
-------------

.. code-block:: sh

    $ make testenv
    $ make test

By default, tests are run with whatever django version is installed. If you want to run tests for other versions
use tox:


.. code-block:: sh

    $ make testenv
    $ tox -e 3.7-2.0.x # or any other environment defined in our tox.ini
