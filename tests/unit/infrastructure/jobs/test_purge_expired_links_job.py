import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob

pytestmark = pytest.mark.filterwarnings("ignore:coroutine '.*' was never awaited")


class TestPurgeExpiredLinksJob:
    

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
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task
            await job.start()
            mock_create_task.assert_called_once()
            
            call_arg = mock_create_task.call_args[0][0]
            assert asyncio.iscoroutine(call_arg)
            assert job._task is mock_task

    @pytest.mark.asyncio
    async def test_stop_with_task(self, job):
        
        
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
        
        job._task = None
        job._stop_event = Mock()
        job._stop_event.set = Mock()
        
        await job.stop()
        job._stop_event.set.assert_called_once()
        

    @pytest.mark.asyncio
    async def test_run_loop_stops_when_event_set(self, job):
        
        job._stop_event = Mock()
        job._stop_event.is_set = Mock(side_effect=[False, True])  
        job._purge_batch = AsyncMock()
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await job._run()
            job._purge_batch.assert_awaited_once()
            mock_sleep.assert_awaited_once_with(10)
        

    @pytest.mark.asyncio
    async def test_run_loop_catches_exception(self, job):
        
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
        
        mock_uow = AsyncMock()
        
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
        
        assert job._cache.invalidate.await_count == 2
        job._cache.invalidate.assert_has_awaits([call("abc123"), call("def456")])
        mock_logger.info.assert_called_once_with("Purged %d expired links", 2)

    @pytest.mark.asyncio
    async def test_purge_batch_no_links(self, job, mock_uow_factory):
        
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
        mock_logger.info.assert_not_called()  

    @pytest.mark.asyncio
    async def test_purge_batch_logs_error_if_cache_fails(self, job, mock_uow_factory):
        
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
            
            with pytest.raises(Exception, match="Cache error"):
                await job._purge_batch()

        
        assert job._cache.invalidate.await_count == 2
        
        mock_logger.info.assert_called_once_with("Purged %d expired links", 2)