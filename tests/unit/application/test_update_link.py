import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from sqlalchemy.exc import IntegrityError

from src.application.use_cases.update_link import UpdateLinkUseCase
from src.application.dto.link_dto import UpdateLinkRequest
from src.application.errors.errors import (
    LinkNotFoundError,
    ShortCodeAlreadyExistsError,
    UserNotAuthorizedError,
    ValidationError,
)
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestUpdateLinkUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.projects = AsyncMock()
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return UpdateLinkUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_short_code(self):
        return "abc123"


    @pytest.fixture
    def sample_link(self, sample_user_id):
        link = Mock()
        link.id = uuid4()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.value = "abc123"
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.expires_at = None
        link.project_id = None
        link.is_owner = Mock(return_value=True)
        link.update_original_url = Mock()
        link.update_short_code = Mock()
        link.update_expires_at = Mock()
        link.update_project_id = Mock()
        return link

    async def test_update_by_owner(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(
            original_url="https://new-example.com",
            short_code="newcode456",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        mock_uow.links.get_by_short_code.assert_called_once_with(sample_short_code)
        sample_link.is_owner.assert_called_once_with(sample_user_id)
        sample_link.update_original_url.assert_called_once()
        sample_link.update_short_code.assert_called_once()
        sample_link.update_expires_at.assert_called_once()
        mock_uow.links.update.assert_called_once_with(sample_link)
        mock_uow.commit.assert_called_once()

    async def test_update_denied_non_owner(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        sample_link.is_owner = Mock(return_value=False)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(original_url="https://new-example.com")

        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_original_url.assert_not_called()
        mock_uow.links.update.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_link_not_found(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=None)
        request = UpdateLinkRequest(original_url="https://new-example.com")

        with pytest.raises(LinkNotFoundError):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

    async def test_update_original_url(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        new_url = "https://new-example.com"
        request = UpdateLinkRequest(original_url=new_url)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_original_url.assert_called_once()
        
        arg = sample_link.update_original_url.call_args[0][0]
        assert isinstance(arg, OriginalUrl)
        assert arg.value == new_url

    async def test_update_short_code(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        new_short_code = "newcode456"
        request = UpdateLinkRequest(short_code=new_short_code)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_short_code.assert_called_once()
        arg = sample_link.update_short_code.call_args[0][0]
        assert isinstance(arg, ShortCode)
        assert arg.value == new_short_code

    async def test_short_code_conflict(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.commit.side_effect = IntegrityError(None, None, None)
        request = UpdateLinkRequest(short_code="newcode456")

        with pytest.raises(ShortCodeAlreadyExistsError):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        mock_uow.rollback.assert_not_called()

    async def test_update_expires_at(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        request = UpdateLinkRequest(expires_at=new_expires_at)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_expires_at.assert_called_once()
        arg = sample_link.update_expires_at.call_args[0][0]
        assert isinstance(arg, ExpiresAt)
        
        assert arg.value == new_expires_at.replace(second=0, microsecond=0)

    async def test_clear_expires_at(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        sample_link.expires_at = Mock(spec=ExpiresAt)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(expires_at=None)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_expires_at.assert_called_once_with(None)

    async def test_update_project_id(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_project = Mock()
        mock_project.is_owner = Mock(return_value=True)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        new_project_id = uuid4()
        request = UpdateLinkRequest(project_id=new_project_id)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(new_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        sample_link.update_project_id.assert_called_once_with(new_project_id)

    async def test_project_not_found(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(project_id=uuid4())

        with pytest.raises(ValidationError, match="Project not found"):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_project_id.assert_not_called()
        mock_uow.links.update.assert_not_called()

    async def test_project_not_owned_by_user(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_project = Mock()
        mock_project.is_owner = Mock(return_value=False)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(project_id=uuid4())

        with pytest.raises(ValidationError, match="Project does not belong to user"):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

    async def test_anonymous_user_cannot_update_link(
            self,
            use_case,
            mock_uow,
            sample_short_code,
            sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(project_id=uuid4())

        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(sample_short_code, request, actor_user_id=None)

    async def test_clear_project_id(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        sample_link.project_id = uuid4()
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(project_id=None)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_project_id.assert_called_once_with(None)

    async def test_invalid_original_url_validation(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(original_url="invalid-url")

        with pytest.raises(ValidationError):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

    async def test_invalid_short_code_validation(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        request = UpdateLinkRequest(short_code="invalid@code")

        with pytest.raises(ValidationError):
            await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

    async def test_invalid_expires_at_validation(
        self,
        use_case,
        mock_uow,
        sample_short_code,
        sample_user_id,
        sample_link,
    ):
        mock_uow.links.get_by_short_code = AsyncMock(return_value=sample_link)
        mock_uow.links.update = AsyncMock()
        mock_uow.commit = AsyncMock()
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        request = UpdateLinkRequest(expires_at=past_date)

        await use_case.execute(sample_short_code, request, actor_user_id=sample_user_id)

        sample_link.update_expires_at.assert_called_once()
        arg = sample_link.update_expires_at.call_args[0][0]
        assert isinstance(arg, ExpiresAt)
        
        assert arg.value == past_date.replace(second=0, microsecond=0)
        mock_uow.links.update.assert_called_once_with(sample_link)
        mock_uow.commit.assert_called_once()

    async def test_invalid_short_code_parameter(self, use_case, sample_user_id):
        invalid_short_code = "invalid@code"
        request = UpdateLinkRequest(original_url="https://example.com")

        with pytest.raises(ValidationError):
            await use_case.execute(invalid_short_code, request, actor_user_id=sample_user_id)