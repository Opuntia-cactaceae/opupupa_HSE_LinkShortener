import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.login_user import LoginUserUseCase
from src.application.dto.auth_dto import AuthResponse, LoginUserRequest
from src.application.errors.errors import InvalidCredentialsError, UserNotFoundError
from src.application.services.password_hasher import PasswordHasher
from src.domain.entities.user import User


class TestLoginUserUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.users = AsyncMock()
        return uow

    @pytest.fixture
    def mock_token_provider(self):
        provider = Mock()
        provider.encode = Mock(return_value="fake.jwt.token")
        return provider

    @pytest.fixture
    def mock_password_hasher(self):
        hasher = Mock(spec=PasswordHasher)
        hasher.verify = Mock(return_value=True)
        return hasher

    @pytest.fixture
    def use_case(self, mock_uow, mock_password_hasher, mock_token_provider):
        return LoginUserUseCase(uow=mock_uow, password_hasher=mock_password_hasher, token_provider=mock_token_provider)

    @pytest.fixture
    def sample_email(self):
        return "test@example.com"

    @pytest.fixture
    def sample_password(self):
        return "password123"

    @pytest.fixture
    def sample_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.password_hash = "hashed_password"
        return user

    async def test_successful_login(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        mock_token_provider,
        sample_email,
        sample_password,
        sample_user,
    ):
        """Test successful login."""
        # Arrange
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        request = LoginUserRequest(email=sample_email, password=sample_password)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert isinstance(result, AuthResponse)
        assert result.access_token == "fake.jwt.token"
        assert result.token_type == "bearer"

        # Verify interactions
        mock_uow.users.get_by_email.assert_called_once_with(sample_email)
        mock_password_hasher.verify.assert_called_once_with(sample_password, sample_user.password_hash)
        mock_token_provider.encode.assert_called_once_with(sample_user.id)

    async def test_user_not_found(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        mock_token_provider,
        sample_email,
        sample_password,
    ):
        """Test UserNotFoundError when user does not exist."""
        # Arrange
        mock_uow.users.get_by_email = AsyncMock(return_value=None)
        request = LoginUserRequest(email=sample_email, password=sample_password)

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await use_case.execute(request)

        # Verify no password verification or token generation
        mock_password_hasher.verify.assert_not_called()
        mock_token_provider.encode.assert_not_called()

    async def test_invalid_password(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        mock_token_provider,
        sample_email,
        sample_password,
        sample_user,
    ):
        """Test InvalidCredentialsError when password is incorrect."""
        # Arrange
        mock_password_hasher.verify.return_value = False
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        request = LoginUserRequest(email=sample_email, password=sample_password)

        # Act & Assert
        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(request)

        # Verify password verification called but no token generation
        mock_password_hasher.verify.assert_called_once_with(sample_password, sample_user.password_hash)
        mock_token_provider.encode.assert_not_called()

    async def test_token_provider_called_with_user_id(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        mock_token_provider,
        sample_email,
        sample_password,
        sample_user,
    ):
        """Test that token provider receives correct user ID."""
        # Arrange
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        request = LoginUserRequest(email=sample_email, password=sample_password)

        # Act
        await use_case.execute(request)

        # Verify password verification
        mock_password_hasher.verify.assert_called_once_with(sample_password, sample_user.password_hash)

        # Assert
        mock_token_provider.encode.assert_called_once_with(sample_user.id)