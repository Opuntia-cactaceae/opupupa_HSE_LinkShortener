import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.resolve_link import ResolveLinkUseCase
from src.application.dto.link_dto import ResolveLinkResponse
from src.application.errors.errors import (
    LinkNotFoundError,
    LinkNotAvailableError,
    ValidationError,
)
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestResolveLinkUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.stats = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def mock_time_provider(self):
        provider = Mock()
        provider.now = Mock(return_value=datetime.now(timezone.utc))
        return provider

    @pytest.fixture
    def use_case(self, mock_uow, mock_time_provider):
        return ResolveLinkUseCase(uow=mock_uow, time_provider=mock_time_provider)

    @pytest.fixture
    def sample_short_code(self):
        return "abc123"

    @pytest.fixture
    def sample_link(self):
        link = Mock()
        link.id = uuid4()
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.original_url.__str__ = Mock(return_value="https://example.com")
        link.expires_at = None
        link.is_available = Mock(return_value=True)
        return link

    async def test_successful_resolve(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_short_code,
        sample_link,
    ):
        """Test successful link resolve."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.increment_click = AsyncMock()
        mock_time_provider.now.return_value = datetime.now(timezone.utc)

        # Act
        result = await use_case.execute(sample_short_code)

        # Assert
        assert isinstance(result, ResolveLinkResponse)
        assert result.original_url == "https://example.com"
        assert result.expires_at is None
        assert result.link_id == sample_link.id

        # Verify interactions
        mock_uow.links.get_by_short_code.assert_called_once_with(sample_short_code)
        mock_uow.stats.increment_click.assert_called_once_with(sample_link.id, mock_time_provider.now.return_value)
        mock_uow.commit.assert_called_once()

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

        # Verify no stats update or commit
        mock_uow.stats.increment_click.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_link_expired(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_short_code,
        sample_link,
    ):
        """Test LinkNotAvailableError when link is expired."""
        # Arrange
        sample_link.is_available = Mock(return_value=False)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_time_provider.now.return_value = datetime.now(timezone.utc)

        # Act & Assert
        with pytest.raises(LinkNotAvailableError):
            await use_case.execute(sample_short_code)

        # Verify no stats update or commit
        mock_uow.stats.increment_click.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_link_with_expiration(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_short_code,
    ):
        """Test successful resolve for link with expiration date."""
        # Arrange
        link = Mock()
        link.id = uuid4()
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.original_url.__str__ = Mock(return_value="https://example.com")
        expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        link.expires_at = Mock(spec=ExpiresAt)
        link.expires_at.value = expires_at
        link.is_available = Mock(return_value=True)

        mock_uow.links.get_by_short_code = AsyncMock(return_value=link)
        mock_uow.stats.increment_click = AsyncMock()
        mock_time_provider.now.return_value = datetime.now(timezone.utc)

        # Act
        result = await use_case.execute(sample_short_code)

        # Assert
        assert result.expires_at == expires_at

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

    async def test_stats_increment_called_with_correct_time(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_short_code,
        sample_link,
    ):
        """Test that increment_click is called with current time."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_time_provider.now.return_value = now
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.stats.increment_click = AsyncMock()

        # Act
        await use_case.execute(sample_short_code)

        # Assert
        mock_uow.stats.increment_click.assert_called_once_with(sample_link.id, now)

    async def test_link_deleted(
        self,
        use_case,
        mock_uow,
        mock_time_provider,
        sample_short_code,
        sample_link,
    ):
        """Test LinkNotAvailableError when link is deleted."""
        # Arrange
        sample_link.is_available = Mock(return_value=False)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)

        # Act & Assert
        with pytest.raises(LinkNotAvailableError):
            await use_case.execute(sample_short_code)

        # Verify no stats update
        mock_uow.stats.increment_click.assert_not_called()
        mock_uow.commit.assert_not_called()