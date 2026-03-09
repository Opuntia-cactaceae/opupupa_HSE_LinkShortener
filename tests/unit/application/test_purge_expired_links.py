import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch

from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
from src.domain.entities.link import Link


class TestPurgeExpiredLinksUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def mock_time_provider(self):
        provider = Mock()
        provider.now = Mock(return_value=datetime.now(timezone.utc))
        return provider

    @pytest.fixture
    def use_case(self, mock_uow, mock_time_provider):
        return PurgeExpiredLinksUseCase(uow=mock_uow, time_provider=mock_time_provider)

    @pytest.fixture
    def sample_link(self):
        link = Mock(spec=Link)
        link.mark_expired = Mock()
        return link

    async def test_purge_expired_links(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_link,
    ):
        """Test marking expired links as expired."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.list_expired = AsyncMock(return_value=[sample_link])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[])
        mock_uow.links.update = AsyncMock()

        # Act
        result = await use_case.execute()

        # Assert
        mock_time_provider.now.assert_called_once()
        mock_uow.links.list_expired.assert_called_once_with(now, 1000)
        sample_link.mark_expired.assert_called_once_with(now)
        mock_uow.links.update.assert_called_once_with(sample_link)
        mock_uow.commit.assert_called_once()
        assert result == [sample_link]

    async def test_purge_stale_links(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_link,
    ):
        """Test marking stale links as expired."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.list_expired = AsyncMock(return_value=[])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[sample_link])
        mock_uow.links.update = AsyncMock()

        # Act
        result = await use_case.execute()

        # Assert
        mock_uow.links.find_stale_links.assert_called_once()
        sample_link.mark_expired.assert_called_once_with(now)
        mock_uow.links.update.assert_called_once_with(sample_link)
        mock_uow.commit.assert_called_once()
        assert result == [sample_link]

    async def test_batch_size(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
    ):
        """Test batch size parameter is passed to repository methods."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.list_expired = AsyncMock(return_value=[])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[])

        # Act
        await use_case.execute(batch_size=500)

        # Assert
        mock_uow.links.list_expired.assert_called_once_with(now, 500)
        mock_uow.links.find_stale_links.assert_called_once()

    async def test_multiple_expired_links(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
    ):
        """Test marking multiple expired links."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        link1 = Mock(spec=Link)
        link1.mark_expired = Mock()
        link2 = Mock(spec=Link)
        link2.mark_expired = Mock()
        mock_uow.links.list_expired = AsyncMock(return_value=[link1, link2])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[])
        mock_uow.links.update = AsyncMock()

        # Act
        result = await use_case.execute()

        # Assert
        assert mock_uow.links.update.call_count == 2
        link1.mark_expired.assert_called_once_with(now)
        link2.mark_expired.assert_called_once_with(now)
        assert result == [link1, link2]

    async def test_mixed_expired_and_stale_links(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
    ):
        """Test both expired and stale links are processed."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        expired_link = Mock(spec=Link)
        expired_link.mark_expired = Mock()
        stale_link = Mock(spec=Link)
        stale_link.mark_expired = Mock()
        mock_uow.links.list_expired = AsyncMock(return_value=[expired_link])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[stale_link])
        mock_uow.links.update = AsyncMock()

        # Act
        result = await use_case.execute()

        # Assert
        assert mock_uow.links.update.call_count == 2
        expired_link.mark_expired.assert_called_once_with(now)
        stale_link.mark_expired.assert_called_once_with(now)
        assert result == [expired_link, stale_link]

    @patch('src.application.use_cases.purge_expired_links.settings')
    async def test_stale_threshold_calculation(
        self,
        mock_settings,
        use_case,
        mock_uow,
        mock_time_provider,
    ):
        """Test stale threshold uses settings.UNUSED_LINK_TTL_DAYS."""
        # Arrange
        mock_settings.UNUSED_LINK_TTL_DAYS = 90
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.list_expired = AsyncMock(return_value=[])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[])

        # Act
        await use_case.execute()

        # Assert
        expected_threshold = now - timedelta(days=90)
        mock_uow.links.find_stale_links.assert_called_once_with(expected_threshold, 1000)

    async def test_no_links_to_purge(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
    ):
        """Test when no expired or stale links exist."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.list_expired = AsyncMock(return_value=[])
        mock_uow.links.find_stale_links = AsyncMock(return_value=[])

        # Act
        result = await use_case.execute()

        # Assert
        assert result == []
        mock_uow.commit.assert_called_once()