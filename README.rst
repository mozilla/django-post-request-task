django-post-request-task
========================

A celery task class whose execution is delayed until after the request
finishes, using request_started and request_finished signals from django and
thread locals.

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
