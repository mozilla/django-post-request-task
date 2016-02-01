from django.core.signals import (got_request_exception, request_finished,
                                 request_started)
from django.test import TestCase

from celery import current_app
from mock import Mock, patch
from post_request_task.task import (task, _get_task_queue, _discard_tasks,
                                    _start_queuing_tasks, _stop_queuing_tasks,
                                    is_task_queuing_enabled_for_this_thread)


current_app.conf.CELERY_ALWAYS_EAGER = True


task_mock = Mock()


@task
def test_task():
    task_mock()


@task
def test_task_with_args_and_kwargs(foo, bar=None):
    task_mock(foo, bar=bar)


class TestTask(TestCase):

    def setUp(self):
        super(TestTask, self).setUp()
        task_mock.reset_mock()
        _discard_tasks()

    def tearDown(self):
        task_mock.reset_mock()
        _discard_tasks()
        _stop_queuing_tasks()
        super(TestTask, self).tearDown()

    def _verify_one_task_queued(self):
        self._verify_x_tasks_queued(1, ((),), ({},))

    def _verify_x_tasks_queued(
            self, expected_size, expected_args, expected_kwargs,
            expected_extra_kw=None, test_task=test_task):
        queue = _get_task_queue()
        size = len(queue)
        self.assertEqual(
            size, expected_size,
            'Expected %d task in the queue, found %d.' % (expected_size, size))
        for i, item in enumerate(queue):
            cls, args, kwargs, extrakw = item
            self.assertEqual(
                cls.name,
                '%s.%s' % (test_task.__module__, test_task.__name__),
                'Expected the test task, found %s.' % cls.name)
            self.assertEqual(
                args,
                expected_args[i],
                'Expected args %s, found %s.' % (expected_args[i], args))
            self.assertEqual(
                kwargs,
                expected_kwargs[i],
                'Expected kwargs %s, found %s.' % (expected_kwargs[i], kwargs))
            if expected_extra_kw:
                self.assertEqual(
                    extrakw,
                    expected_extra_kw[i],
                    'Expected extra kwargs %s, found %s.' % (
                        expected_extra_kw[i], extrakw))

    def _verify_task_empty(self):
        assert len(_get_task_queue()) == 0, (
            'Expected empty queue, got %s: %s' % (len(_get_task_queue()),
                                                  _get_task_queue()))

    def test_task_queue_is_enabled(self):
        self.assertEqual(is_task_queuing_enabled_for_this_thread(), False)
        _start_queuing_tasks()
        self.assertEqual(is_task_queuing_enabled_for_this_thread(), True)
        _stop_queuing_tasks()
        self.assertEqual(is_task_queuing_enabled_for_this_thread(), False)

    def test_task_should_be_called_immediately(self):
        result = test_task.delay()
        self.assertTrue(result)
        self.assertEqual(task_mock.call_count, 1)

    def test_task_with_args_and_kwargs(self):
        test_task_with_args_and_kwargs.delay(42, bar='rista')
        self.assertEqual(task_mock.call_count, 1)
        self.assertEqual(task_mock.call_args[0], (42,))
        self.assertEqual(task_mock.call_args[1], {'bar': 'rista'})

    def test_task_in_request_should_not_be_called_immediately(self):
        request_started.send(sender=self)
        result = test_task.delay()
        self.assertEqual(result, None)
        self.assertEqual(task_mock.call_count, 0)

    def test_task_in_request_with_args_and_kwargs(self):
        request_started.send(sender=self)
        test_task.delay(42, foo='bar')
        self.assertEqual(task_mock.call_count, 0)

    @patch('post_request_task.task.PostRequestTask.original_apply_async')
    def test_task_applied_once_request_finished(
            self, original_apply_async_mock):
        request_started.send(sender=self)
        test_task.delay()
        self._verify_one_task_queued()

        request_finished.send(sender=self)
        self._verify_task_empty()

        # Assert the original `apply_async` called.
        self.assertEqual(
            original_apply_async_mock.call_count, 1,
            'Expected PostRequestTask.original_apply_async call')

    @patch('post_request_task.task.PostRequestTask.original_apply_async')
    def test_task_discarded_when_request_failed(
            self, original_apply_async_mock):
        request_started.send(sender=self)
        test_task.delay()
        self._verify_one_task_queued()

        # Simulate a request exception.
        got_request_exception.send(sender=self)
        self._verify_task_empty()

        # Assert the original `apply_async` was not called.
        self.assertEqual(
            original_apply_async_mock.call_count, 0,
            'Unexpected PostRequestTask.original_apply_async call')

    def test_deduplication(self):
        """Test the same task added multiple times is de-duped."""
        request_started.send(sender=self)
        test_task.delay()
        test_task.delay()

        self._verify_one_task_queued()

    def test_tasks_deduplication_with_different_arguments(self):
        """Test arguments sent to the task are used when de-duping."""
        request_started.send(sender=self)
        test_task_with_args_and_kwargs.delay(42)
        test_task_with_args_and_kwargs.delay(42, bar='rista')
        test_task_with_args_and_kwargs.delay(42, bar='rista')

        self._verify_x_tasks_queued(
            2,  # 2 tasks should have been kept.
            ((42,), (42,)),  # Each of those tasks sent "42" as the only arg...
            ({}, {'bar': 'rista'}),  # ... Only the second one sent kwargs.
            test_task=test_task_with_args_and_kwargs)

    def test_tasks_deduplication_with_different_keyword_arguments(self):
        """Test keyword arguments sent to the task are used when de-duping."""
        request_started.send(sender=self)
        test_task_with_args_and_kwargs.delay(42, bar='rista')
        test_task_with_args_and_kwargs.delay(42, bar='rista')
        test_task_with_args_and_kwargs.delay(42, bar='atheon')
        test_task_with_args_and_kwargs.delay(42, bar='rage')
        test_task_with_args_and_kwargs.delay(42, bar='rista')
        test_task_with_args_and_kwargs.delay(42, bar='rage')

        self._verify_x_tasks_queued(
            3,
            ((42,), (42,), (42, )),
            ({'bar': 'rista'}, {'bar': 'atheon'}, {'bar': 'rage'}),
            test_task=test_task_with_args_and_kwargs)

    def test_tasks_deduplication_with_celery_keywords(self):
        """Test celery-specific keyword arguments are used when de-duping."""
        request_started.send(sender=self)
        # Note that we are using apply_async() instead of delay() to allow us
        # to pass celery-specific arguments, as a result we have to send the
        # positional arguments with args=() and the keyword arguments with
        # kwargs={}. Everything else is an argument to the apply_async() call
        # itself.
        test_task_with_args_and_kwargs.apply_async(
            args=(42,), kwargs={'bar': 'rista'}, retry=3)
        test_task_with_args_and_kwargs.apply_async(
            args=(42,), kwargs={'bar': 'rista'}, retry=1)
        test_task_with_args_and_kwargs.apply_async(
            args=(42,), kwargs={'bar': 'rista'}, retry=3)

        self._verify_x_tasks_queued(
            2,
            ((42, ), (42, )),
            ({'bar': 'rista'}, {'bar': 'rista'}),
            ({'retry': 3}, {'retry': 1}),
            test_task=test_task_with_args_and_kwargs)
