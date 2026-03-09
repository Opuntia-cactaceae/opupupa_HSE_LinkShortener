import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.delete_link import DeleteLinkUseCase
from src.application.errors.errors import (
    LinkNotFoundError,
    UserNotAuthorizedError,
    ValidationError,
)
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl


class TestDeleteLinkUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return DeleteLinkUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_short_code(self):
        return "abc123"

    @pytest.fixture
    def sample_user_id(self):
        return uuid4()

    @pytest.fixture
    def sample_link(self, sample_user_id):
        link = Mock()
        link.id = uuid4()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.value = "abc123"
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.is_owner = Mock(return_value=True)
        link.delete = Mock()
        return link

    async def test_delete_by_owner(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        """Test successful deletion by owner."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)

        # Act
        await use_case.execute(sample_short_code, actor_user_id=sample_user_id)

        # Assert
        mock_uow.links.get_by_short_code.assert_called_once_with(sample_short_code)
        sample_link.is_owner.assert_called_once_with(sample_user_id)
        sample_link.delete.assert_called_once()
        mock_uow.links.update.assert_called_once_with(sample_link)
        mock_uow.commit.assert_called_once()

    async def test_delete_denied_non_owner(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        """Test UserNotAuthorizedError when non-owner tries to delete."""
        # Arrange
        sample_link.is_owner = Mock(return_value=False)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)

        # Act & Assert
        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(sample_short_code, actor_user_id=sample_user_id)

        # Verify no delete or commit
        sample_link.delete.assert_not_called()
        mock_uow.links.update.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_link_not_found(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
    ):
        """Test LinkNotFoundError when link does not exist."""
        # Arrange
        mock_uow.links.get_by_short_code = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(LinkNotFoundError):
            await use_case.execute(sample_short_code, actor_user_id=sample_user_id)

    async def test_delete_anonymous_link_by_anonymous_user(
        self,
        use_case,
        mock_uow,
        sample_short_code,
    ):
        """Test anonymous user can delete anonymous link (owner_user_id is None)."""
        # Arrange
        link = Mock()
        link.is_owner = Mock(return_value=True)  # is_owner(None) returns True
        link.delete = Mock()
        mock_uow.links.get_by_short_code = AsyncMock(return_value=link)

        # Act
        await use_case.execute(sample_short_code, actor_user_id=None)

        # Assert
        link.is_owner.assert_called_once_with(None)
        link.delete.assert_called_once()
        mock_uow.links.update.assert_called_once_with(link)
        mock_uow.commit.assert_called_once()

    async def test_delete_anonymous_link_by_authenticated_user(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
    ):
        """Test authenticated user cannot delete anonymous link."""
        # Arrange
        link = Mock()
        link.is_owner = Mock(return_value=False)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=link)

        # Act & Assert
        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(sample_short_code, actor_user_id=sample_user_id)

    async def test_invalid_short_code_validation(
        self,
        use_case,
        sample_short_code,
        sample_user_id,
    ):
        """Test validation error for invalid short code."""
        # Arrange
        invalid_code = "a"  # too short

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(invalid_code, actor_user_id=sample_user_id)

    async def test_short_code_with_invalid_characters(
        self,
        use_case,
        sample_user_id,
    ):
        """Test validation error for short code with invalid characters."""
        # Arrange
        invalid_code = "abc@123"

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(invalid_code, actor_user_id=sample_user_id)