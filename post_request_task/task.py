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
    _locals.__dict__['task_queue_enabled'] = True


def _stop_queuing_tasks(**kwargs):
    """Stops queuing tasks for this thread.

    Not supposed to be called directly, only useful for tests cleanup."""
    _locals.__dict__['task_queue_enabled'] = False


def is_task_queuing_enabled_for_this_thread():
    """Returns whether post request task queuing is enabled for this thread."""
    return _locals.__dict__.get('task_queue_enabled', False)


def _send_tasks_and_stop_queuing(**kwargs):
    """Sends all delayed Celery tasks and stop queuing new ones for now."""
    log.info('Stopping queueing tasks and sending already queued ones.')
    _stop_queuing_tasks()
    task_queue = _get_task_queue()
    while task_queue:
        task, args, kwargs, extrakw = task_queue.pop(0)
        task.original_apply_async(args=args, kwargs=kwargs, **extrakw)


def _discard_tasks(**kwargs):
    """Discards all delayed Celery tasks."""
    task_queue = _get_task_queue()
    log.info('Discarding %d queued tasks.', len(task_queue))
    task_queue[:] = []


def _append_task(t):
    """Append a task to the queue.

    Expected argument is a tuple of the following form:
    (task class, args, kwargs, extra kwargs).

    This doesn't append to queue if the argument is already in the queue.

    """
    task_queue = _get_task_queue()
    if t not in task_queue:
        log.debug('Appended new task to the queue: %s.', t)
        task_queue.append(t)
    else:
        log.debug('Did not append duplicate task to the queue: %s.', t)
    return None


class PostRequestTask(Task):
    """A task whose execution is delayed until after the request finishes.

    This simply wraps celery's `@task` decorator and stores the task calls
    until after the request is finished, then fires them off.

    If no request was started in this thread, behaves exactly like the original
    @task decorator, sending tasks to celery directly.
    """
    abstract = True

    def original_apply_async(self, args=None, kwargs=None, **extrakw):
        return super(PostRequestTask, self).apply_async(
            args=args, kwargs=kwargs, **extrakw)

    def apply_async(self, args=None, kwargs=None, **extrakw):
        if is_task_queuing_enabled_for_this_thread():
            result = _append_task((self, args, kwargs, extrakw))
        else:
            result = self.original_apply_async(
                args=args, kwargs=kwargs, **extrakw)
        return result


# Replacement `@task` decorator.
task = partial(base_task, base=PostRequestTask)


# Hook the signal handlers up.
# Start queuing the tasks only if we're inside a request-response cycle thread.
request_started.connect(
    _start_queuing_tasks, dispatch_uid='{}.request_started'.format(__name__))

# Send the tasks to celery and stop queuing when the request is finished.
request_finished.connect(
    _send_tasks_and_stop_queuing,
    dispatch_uid='{}.request_finished'.format(__name__))

# And make sure to discard the task queue when we have an exception in the
# request-response cycle.
got_request_exception.connect(
    _discard_tasks, dispatch_uid='{}.got_request_exception'.format(__name__))
