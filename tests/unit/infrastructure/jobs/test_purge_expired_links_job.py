import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob

pytestmark = pytest.mark.filterwarnings("ignore:coroutine '.*' was never awaited")


class TestPurgeExpiredLinksJob:
    """Unit tests for PurgeExpiredLinksJob."""

    @pytest.fixture
    def mock_uow_factory(self):
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def job(self, mock_uow_factory, mock_cache):
        return PurgeExpiredLinksJob(
            uow_factory=mock_uow_factory,
            cache=mock_cache,
            interval_sec=10,
        )

    @pytest.mark.asyncio
    async def test_init(self, mock_uow_factory, mock_cache):
        """Test constructor sets attributes."""
        job = PurgeExpiredLinksJob(
            uow_factory=mock_uow_factory,
            cache=mock_cache,
            interval_sec=30,
        )
        assert job._uow_factory is mock_uow_factory
        assert job._cache is mock_cache
        assert job._interval_sec == 30
        assert job._task is None
        assert isinstance(job._stop_event, asyncio.Event)

    @pytest.mark.asyncio
    async def test_start_creates_task(self, job):
        """Test start creates asyncio task."""
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task
            await job.start()
            mock_create_task.assert_called_once()
            # Ensure the task argument is a coroutine (job._run)
            call_arg = mock_create_task.call_args[0][0]
            assert asyncio.iscoroutine(call_arg)
            assert job._task is mock_task

    @pytest.mark.asyncio
    async def test_stop_with_task(self, job):
        """Test stop sets stop event and awaits task."""
        # Create a future that's already done so await returns immediately
        future = asyncio.Future()
        future.set_result(None)
        job._task = future
        job._stop_event = Mock()
        job._stop_event.set = Mock()

        await job.stop()
        job._stop_event.set.assert_called_once()
        assert job._task is None

    @pytest.mark.asyncio
    async def test_stop_without_task(self, job):
        """Test stop when task is None."""
        job._task = None
        job._stop_event = Mock()
        job._stop_event.set = Mock()
        # Should not raise
        await job.stop()
        job._stop_event.set.assert_called_once()
        # No await on task

    @pytest.mark.asyncio
    async def test_run_loop_stops_when_event_set(self, job):
        """Test _run loop exits when stop event is set."""
        job._stop_event = Mock()
        job._stop_event.is_set = Mock(side_effect=[False, True])  # first loop iteration, then stop
        job._purge_batch = AsyncMock()
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await job._run()
            job._purge_batch.assert_awaited_once()
            mock_sleep.assert_awaited_once_with(10)
        # Should log start and stop (but we don't assert logs)

    @pytest.mark.asyncio
    async def test_run_loop_catches_exception(self, job):
        """Test _run catches exceptions and logs."""
        job._stop_event = Mock()
        job._stop_event.is_set = Mock(side_effect=[False, True])
        job._purge_batch = AsyncMock(side_effect=Exception("Test error"))
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep, \
             patch('src.infrastructure.jobs.purge_expired_links_job.logger') as mock_logger:
            await job._run()
            job._purge_batch.assert_awaited_once()
            mock_sleep.assert_awaited_once_with(10)
            mock_logger.exception.assert_called_once()
            assert "Error in purge job" in mock_logger.exception.call_args[0][0]

    @pytest.mark.asyncio
    async def test_purge_batch_success(self, job, mock_uow_factory):
        """Test _purge_batch calls use case and invalidates cache."""
        mock_uow = AsyncMock()
        # mock_uow_factory must return an async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_factory.return_value = mock_context

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value=[Mock(short_code="abc123"), Mock(short_code="def456")])
        with patch('src.infrastructure.jobs.purge_expired_links_job.PurgeExpiredLinksUseCase') as MockUseCase, \
             patch('src.infrastructure.jobs.purge_expired_links_job.SystemTimeProvider') as MockTimeProvider:
            MockUseCase.return_value = mock_use_case
            MockTimeProvider.return_value = Mock()
            with patch('src.infrastructure.jobs.purge_expired_links_job.logger') as mock_logger:
                await job._purge_batch()

        mock_uow_factory.assert_called_once()
        MockUseCase.assert_called_once_with(mock_uow, MockTimeProvider.return_value)
        mock_use_case.execute.assert_awaited_once()
        # Ensure cache.invalidate called for each purged link
        assert job._cache.invalidate.await_count == 2
        job._cache.invalidate.assert_has_awaits([call("abc123"), call("def456")])
        mock_logger.info.assert_called_once_with("Purged %d expired links", 2)

    @pytest.mark.asyncio
    async def test_purge_batch_no_links(self, job, mock_uow_factory):
        """Test _purge_batch when no links purged."""
        mock_uow = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_factory.return_value = mock_context
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value=[])
        with patch('src.infrastructure.jobs.purge_expired_links_job.PurgeExpiredLinksUseCase') as MockUseCase, \
             patch('src.infrastructure.jobs.purge_expired_links_job.SystemTimeProvider') as MockTimeProvider, \
             patch('src.infrastructure.jobs.purge_expired_links_job.logger') as mock_logger:
            MockUseCase.return_value = mock_use_case
            MockTimeProvider.return_value = Mock()
            await job._purge_batch()

        mock_use_case.execute.assert_awaited_once()
        job._cache.invalidate.assert_not_awaited()
        mock_logger.info.assert_not_called()  # No log for zero purged links

    @pytest.mark.asyncio
    async def test_purge_batch_logs_error_if_cache_fails(self, job, mock_uow_factory):
        """Test _purge_batch continues if cache invalidation fails."""
        mock_uow = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_factory.return_value = mock_context
        mock_use_case = AsyncMock()
        link1 = Mock(short_code="abc123")
        link2 = Mock(short_code="def456")
        mock_use_case.execute = AsyncMock(return_value=[link1, link2])
        job._cache.invalidate = AsyncMock(side_effect=[None, Exception("Cache error")])
        with patch('src.infrastructure.jobs.purge_expired_links_job.PurgeExpiredLinksUseCase') as MockUseCase, \
             patch('src.infrastructure.jobs.purge_expired_links_job.SystemTimeProvider') as MockTimeProvider, \
             patch('src.infrastructure.jobs.purge_expired_links_job.logger') as mock_logger:
            MockUseCase.return_value = mock_use_case
            MockTimeProvider.return_value = Mock()
            # Expect exception to be raised from cache.invalidate
            with pytest.raises(Exception, match="Cache error"):
                await job._purge_batch()

        # Both invalidation attempts made (second raises)
        assert job._cache.invalidate.await_count == 2
        # Logger should still have been called for purge count before exception
        mock_logger.info.assert_called_once_with("Purged %d expired links", 2)