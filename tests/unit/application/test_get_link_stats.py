import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.get_link_stats import GetLinkStatsUseCase
from src.application.dto.link_dto import LinkStatsResponse
from src.application.errors.errors import LinkNotFoundError, ValidationError
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestGetLinkStatsUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.stats = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return GetLinkStatsUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_short_code(self):
        return "abc123"

    @pytest.fixture
    def sample_link(self):
        link = Mock()
        link.id = uuid4()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.value = "abc123"
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.original_url.__str__ = Mock(return_value="https://example.com")
        link.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        link.expires_at = None
        link.owner_user_id = uuid4()
        link.project_id = None
        link.is_expired = Mock(return_value=False)
        return link

    @pytest.fixture
    def sample_stats(self):
        stats = Mock()
        stats.clicks = 42
        stats.last_used_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return stats

    async def test_successful_get_stats(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_link,
        sample_stats,
    ):
        """Test successful stats retrieval."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.get_by_link_id = AsyncMock(return_value=sample_stats)

        # Act
        result = await use_case.execute(sample_short_code)

        # Assert
        assert isinstance(result, LinkStatsResponse)
        assert result.short_code == "abc123"
        assert result.original_url == "https://example.com"
        assert result.created_at == sample_link.created_at
        assert result.clicks == 42
        assert result.last_used_at == sample_stats.last_used_at
        assert result.expires_at is None
        assert result.full_short_url == "http://localhost:8000/opupupa/abc123"
        assert result.is_expired is False
        assert result.project_id is None
        assert result.owner_user_id == sample_link.owner_user_id

        # Verify interactions
        mock_uow.links.get_by_short_code.assert_called_once_with(sample_short_code)
        mock_uow.stats.get_by_link_id.assert_called_once_with(sample_link.id)

    async def test_link_not_found(
        self,
        use_case,
        mock_uow,
        sample_short_code,
    ):
        """Test LinkNotFoundError when link does not exist."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(LinkNotFoundError):
            await use_case.execute(sample_short_code)

        # Verify stats not called
        mock_uow.stats.get_by_link_id.assert_not_called()

    async def test_stats_not_found(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_link,
    ):
        """Test LinkNotFoundError when stats are not found."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.get_by_link_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(LinkNotFoundError):
            await use_case.execute(sample_short_code)

    async def test_link_with_expiration(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_link,
        sample_stats,
    ):
        """Test stats for link with expiration date."""
        # Arrange
        expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        sample_link.expires_at = Mock(spec=ExpiresAt)
        sample_link.expires_at.value = expires_at
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.get_by_link_id = AsyncMock(return_value=sample_stats)

        # Act
        result = await use_case.execute(sample_short_code)

        # Assert
        assert result.expires_at == expires_at

    async def test_link_expired(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_link,
        sample_stats,
    ):
        """Test stats for expired link."""
        # Arrange
        sample_link.is_expired = Mock(return_value=True)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.get_by_link_id = AsyncMock(return_value=sample_stats)

        # Act
        result = await use_case.execute(sample_short_code)

        # Assert
        assert result.is_expired is True

    async def test_invalid_short_code_validation(
        self,
        use_case,
        sample_short_code,
    ):
        """Test validation error for invalid short code."""
        # Arrange
        invalid_code = "a"  # too short

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(invalid_code)

    async def test_short_code_with_invalid_characters(
        self,
        use_case,
    ):
        """Test validation error for short code with invalid characters."""
        # Arrange
        invalid_code = "abc@123"

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(invalid_code)