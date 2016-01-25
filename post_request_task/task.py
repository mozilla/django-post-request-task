import logging
import threading
from functools import partial

from django.core.signals import (got_request_exception, request_finished,
                                 request_started)

from celery import task as base_task
from celery import Task


log = logging.getLogger('post_request_task')


_locals = threading.local()


def _get_task_queue():
    """Returns the calling thread's task queue."""
    return _locals.__dict__.setdefault('task_queue', [])


def _start_queuing_tasks(**kwargs):
    """Starts queuing tasks for this thread.

    Not supposed to be called directly, instead it's connected to the
    request_started signal.

    If not called, tasks are delayed normally (so tasks still function without
    having to call _send_tasks_and_stop_queuing() manually when we're outside
    the request-response cycle.."""
    _locals.__dict__['queue_tasks'] = True


def _stop_queuing_tasks(**kwargs):
    """Stops queuing tasks for this thread.

    Not supposed to be called directly, only useful for tests cleanup."""
    _locals.__dict__.pop('queue_tasks', None)


def is_task_queuing_enabled_for_this_thread():
    """Returns whether post request task queuing is enabled for this thread."""
    return _locals.__dict__.get('queue_tasks', False)


def _send_tasks_and_stop_queuing(**kwargs):
    """Sends all delayed Celery tasks and stop queuing new ones for now."""
    _locals.__dict__.pop('queue_tasks', None)
    queue = _get_task_queue()
    while queue:
        cls, args, kwargs = queue.pop(0)
        cls.original_apply_async(*args, **kwargs)


def _discard_tasks(**kwargs):
    """Discards all delayed Celery tasks."""
    _get_task_queue()[:] = []


def _append_task(t):
    """Append a task to the queue.

    Expected argument is a tuple of the (task class, args, kwargs).

    This doesn't append to queue if the argument is already in the queue.

    """
    queue = _get_task_queue()
    if t not in queue:
        queue.append(t)
    else:
        log.debug('Removed duplicate task: %s' % (t,))


class PostRequestTask(Task):
    """A task whose execution is delayed until after the request finishes.

    This simply wraps celery's `@task` decorator and stores the task calls
    until after the request is finished, then fires them off.

    If no request was started in this thread, behaves exactly like the original
    @task decorator, sending tasks to celery directly.
    """
    abstract = True

    def original_apply_async(self, *args, **kwargs):
        return super(PostRequestTask, self).apply_async(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        if is_task_queuing_enabled_for_this_thread():
            _append_task((self, args, kwargs))
        else:
            self.original_apply_async(*args, **kwargs)


# Replacement `@task` decorator.
task = partial(base_task, base=PostRequestTask)


# Hook the signal handlers up.
# Start queuing the tasks only if we're inside a request-response cycle thread.
request_started.connect(_start_queuing_tasks,
                        dispatch_uid='request_started_tasks')

# Send the tasks to celery and stop queuing when the request is finished.
request_finished.connect(_send_tasks_and_stop_queuing,
                         dispatch_uid='request_finished_tasks')

# And make sure to discard the task queue when we have an exception in the
# request-response cycle.
got_request_exception.connect(_discard_tasks,
                              dispatch_uid='request_exception_tasks')
