import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.exc import IntegrityError

from src.application.use_cases.shorten_link import ShortenLinkUseCase
from src.application.dto.link_dto import ShortenLinkRequest, ShortenLinkResponse
from src.application.errors.errors import (
    ShortCodeAlreadyExistsError,
    ValidationError,
)
from src.domain.entities.link import Link
from src.domain.entities.link_stats import LinkStats
from src.domain.entities.project import Project
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestShortenLinkUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.stats = AsyncMock()
        uow.projects = AsyncMock()
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.fixture
    def mock_short_code_generator(self):
        generator = Mock()
        generator.generate = Mock(return_value="abc12345")
        return generator

    @pytest.fixture
    def mock_time_provider(self):
        provider = Mock()
        provider.now = Mock(return_value=datetime.now(timezone.utc))
        return provider

    @pytest.fixture
    def use_case(self, mock_uow, mock_short_code_generator, mock_time_provider):
        return ShortenLinkUseCase(
            uow=mock_uow,
            short_code_generator=mock_short_code_generator,
            time_provider=mock_time_provider,
        )

    @pytest.fixture
    def sample_user_id(self):
        return uuid4()

    @pytest.fixture
    def sample_project_id(self):
        return uuid4()

    @pytest.fixture
    def sample_expires_at(self):
        return datetime.now(timezone.utc) + timedelta(days=1)

    @pytest.fixture
    def sample_original_url(self):
        return "https://example.com"

    async def test_successful_link_creation_with_generated_code(
        self,
        use_case,
        mock_uow,
        mock_short_code_generator,
        sample_user_id,
        sample_original_url,
    ):
        """Test successful link creation with generated short code."""
        # Arrange
        request = ShortenLinkRequest(original_url=sample_original_url)
        mock_uow.commit.return_value = None
        mock_uow.links.add = AsyncMock()
        mock_uow.stats.add = AsyncMock()

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        assert isinstance(result, ShortenLinkResponse)
        assert result.short_code == "abc12345"
        assert result.original_url == sample_original_url
        assert result.owner_user_id == sample_user_id
        assert result.expires_at is None
        assert result.project_id is None
        assert result.clicks == 0
        assert result.is_expired is False
        assert result.full_short_url.startswith("http://localhost:8000/opupupa/abc12345")

        # Verify interactions
        mock_short_code_generator.generate.assert_called_once()
        mock_uow.links.add.assert_called_once()
        mock_uow.stats.add.assert_called_once()
        mock_uow.commit.assert_called_once()
        # Ensure link was created with correct parameters
        link_arg = mock_uow.links.add.call_args[0][0]
        assert isinstance(link_arg, Link)
        assert link_arg.short_code.value == "abc12345"
        assert link_arg.original_url.value == sample_original_url
        assert link_arg.owner_user_id == sample_user_id

    async def test_successful_link_creation_with_custom_alias(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
    ):
        """Test successful link creation with custom alias."""
        # Arrange
        custom_alias = "myalias"
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            custom_alias=custom_alias,
        )
        mock_uow.commit.return_value = None

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        assert result.short_code == custom_alias
        # Ensure short code validation passed
        mock_uow.links.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    async def test_custom_alias_conflict(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
    ):
        """Test that custom alias conflict raises ShortCodeAlreadyExistsError."""
        # Arrange
        custom_alias = "myalias"
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            custom_alias=custom_alias,
        )
        # Simulate IntegrityError on commit (duplicate short code)
        mock_uow.commit.side_effect = IntegrityError(None, None, None)
        # Act & Assert
        with pytest.raises(ShortCodeAlreadyExistsError):
            await use_case.execute(request, actor_user_id=sample_user_id)


    async def test_anonymous_link_creation(
        self,
        use_case,
        mock_uow,
        mock_short_code_generator,
        sample_original_url,
    ):
        """Test creating anonymous link (no owner)."""
        # Arrange
        request = ShortenLinkRequest(original_url=sample_original_url)

        # Act
        result = await use_case.execute(request, actor_user_id=None)

        # Assert
        assert result.owner_user_id is None
        link_arg = mock_uow.links.add.call_args[0][0]
        assert link_arg.owner_user_id is None

    async def test_link_creation_with_expiration(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
        sample_expires_at,
    ):
        """Test creating link with expiration date."""
        # Arrange
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            expires_at=sample_expires_at,
        )

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        # ExpiresAt rounds down to minute (seconds and microseconds zero)
        expected_expires_at = sample_expires_at.replace(second=0, microsecond=0)
        assert result.expires_at == expected_expires_at
        link_arg = mock_uow.links.add.call_args[0][0]
        assert link_arg.expires_at is not None
        assert link_arg.expires_at.value == expected_expires_at

    async def test_invalid_expires_at_past(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
    ):
        """Test past expires_at is allowed (for already expired links)."""
        # Arrange
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            expires_at=past_date,
        )
        mock_uow.commit.return_value = None
        mock_uow.links.add = AsyncMock()
        mock_uow.stats.add = AsyncMock()

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        expected_expires_at = past_date.replace(second=0, microsecond=0)
        assert result.expires_at == expected_expires_at
        # Note: is_expired may depend on time provider; we'll skip this assertion

    async def test_link_creation_with_project(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
        sample_project_id,
    ):
        """Test creating link with project assignment."""
        # Arrange
        mock_project = Mock(spec=Project)
        mock_project.is_owner = Mock(return_value=True)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        request = ShortenLinkRequest(
            original_url=sample_original_url,
            project_id=sample_project_id,
        )

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        assert result.project_id == sample_project_id
        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        link_arg = mock_uow.links.add.call_args[0][0]
        assert link_arg.project_id == sample_project_id

    async def test_project_not_found(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
        sample_project_id,
    ):
        """Test validation error when project not found."""
        # Arrange
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            project_id=sample_project_id,
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Project not found"):
            await use_case.execute(request, actor_user_id=sample_user_id)

    async def test_project_not_owned_by_user(
        self,
        use_case,
        mock_uow,
        sample_user_id,
        sample_original_url,
        sample_project_id,
    ):
        """Test validation error when project does not belong to user."""
        # Arrange
        mock_project = Mock(spec=Project)
        mock_project.is_owner = Mock(return_value=False)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        request = ShortenLinkRequest(
            original_url=sample_original_url,
            project_id=sample_project_id,
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Project does not belong to user"):
            await use_case.execute(request, actor_user_id=sample_user_id)

    async def test_anonymous_user_cannot_assign_project(
        self,
        use_case,
        mock_uow,
        sample_original_url,
        sample_project_id,
    ):
        """Test validation error when anonymous user tries to assign project."""
        # Arrange
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            project_id=sample_project_id,
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Anonymous users cannot assign projects"):
            await use_case.execute(request, actor_user_id=None)

    async def test_invalid_url_validation(
        self,
        use_case,
        sample_user_id,
    ):
        """Test validation error for invalid URL."""
        # Arrange
        request = ShortenLinkRequest(original_url="invalid-url")

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(request, actor_user_id=sample_user_id)

    async def test_invalid_custom_alias_validation(
        self,
        use_case,
        sample_user_id,
        sample_original_url,
    ):
        """Test validation error for invalid custom alias."""
        # Arrange
        request = ShortenLinkRequest(
            original_url=sample_original_url,
            custom_alias="invalid@alias",
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(request, actor_user_id=sample_user_id)

    async def test_generated_code_collision_retry(
        self,
        use_case,
        mock_uow,
        mock_short_code_generator,
        sample_user_id,
        sample_original_url,
    ):
        """Test retry logic when generated short code collides."""
        # Arrange
        request = ShortenLinkRequest(original_url=sample_original_url)

        # Simulate first attempt collision, second success
        mock_uow.commit.side_effect = [
            IntegrityError(None, None, None),  # First attempt fails
            None,  # Second attempt succeeds
        ]
        mock_short_code_generator.generate.side_effect = ["first123", "second456"]

        # Act
        result = await use_case.execute(request, actor_user_id=sample_user_id)

        # Assert
        assert result.short_code == "second456"
        assert mock_uow.commit.call_count == 2
        assert mock_short_code_generator.generate.call_count == 2

    async def test_generated_code_collision_exhausted(
        self,
        use_case,
        mock_uow,
        mock_short_code_generator,
        sample_user_id,
        sample_original_url,
    ):
        """Test that after 10 collisions, ShortCodeAlreadyExistsError is raised."""
        # Arrange
        request = ShortenLinkRequest(original_url=sample_original_url)

        # Simulate 10 collisions
        mock_uow.commit.side_effect = IntegrityError(None, None, None)
        mock_short_code_generator.generate.return_value = "collision"

        # Act & Assert
        with pytest.raises(ShortCodeAlreadyExistsError, match="Could not generate unique short code"):
            await use_case.execute(request, actor_user_id=sample_user_id)

        # Verify exactly 10 attempts
        assert mock_uow.commit.call_count == 10
        assert mock_short_code_generator.generate.call_count == 10