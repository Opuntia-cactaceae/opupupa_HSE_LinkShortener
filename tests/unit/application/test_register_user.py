import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from src.application.use_cases.register_user import RegisterUserUseCase
from src.application.dto.auth_dto import RegisterUserRequest, RegisterUserResponse
from src.application.errors.errors import EmailAlreadyExistsError, ValidationError
from src.domain.entities.user import User
from src.application.services.password_hasher import PasswordHasher


class TestRegisterUserUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.users = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def mock_password_hasher(self):
        hasher = Mock(spec=PasswordHasher)
        hasher.hash = Mock(return_value="hashed_password")
        hasher.verify = Mock(return_value=True)
        return hasher

    @pytest.fixture
    def use_case(self, mock_uow, mock_password_hasher):
        return RegisterUserUseCase(uow=mock_uow, password_hasher=mock_password_hasher)



    @pytest.fixture
    def sample_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        return user

    async def test_successful_registration(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        sample_email,
        sample_password,
        sample_user,
    ):
        
        
        mock_uow.users.get_by_email = AsyncMock(return_value=None)
        mock_uow.users.add = AsyncMock()
        request = RegisterUserRequest(email=sample_email, password=sample_password)

        with patch('src.application.use_cases.register_user.User') as MockUser:
            MockUser.create = Mock(return_value=sample_user)
            MockUser.validate_password = Mock()
            
            result = await use_case.execute(request)

        
        assert isinstance(result, RegisterUserResponse)
        assert result.user_id == sample_user.id

        
        mock_uow.users.get_by_email.assert_called_once_with(sample_email)
        MockUser.validate_password.assert_called_once_with(sample_password)
        mock_password_hasher.hash.assert_called_once_with(sample_password)
        MockUser.create.assert_called_once_with(sample_email, "hashed_password")
        mock_uow.users.add.assert_called_once_with(sample_user)
        mock_uow.commit.assert_called_once()

    async def test_email_already_exists(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        sample_email,
        sample_password,
        sample_user,
    ):
        
        
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        request = RegisterUserRequest(email=sample_email, password=sample_password)

        
        with pytest.raises(EmailAlreadyExistsError):
            await use_case.execute(request)

        
        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_invalid_email_validation(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        sample_password,
    ):
        
        
        mock_uow.users.get_by_email = AsyncMock(return_value=None)
        request = RegisterUserRequest(email="invalid-email", password=sample_password)

        
        with patch('src.application.use_cases.register_user.User') as MockUser:
            MockUser.create = Mock(side_effect=ValueError("Invalid email format"))
            MockUser.validate_password = Mock()
            
            with pytest.raises(ValidationError, match="Invalid email format"):
                await use_case.execute(request)

        
        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()
        MockUser.validate_password.assert_called_once_with(sample_password)
        mock_password_hasher.hash.assert_called_once_with(sample_password)

    async def test_password_too_short_validation(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        sample_email,
    ):
        
        
        mock_uow.users.get_by_email = AsyncMock(return_value=None)
        request = RegisterUserRequest(email=sample_email, password="short")

        with patch('src.application.use_cases.register_user.User') as MockUser:
            MockUser.validate_password = Mock(side_effect=ValueError("Password must be at least 8 characters"))
            
            with pytest.raises(ValidationError, match="Password must be at least 8 characters"):
                await use_case.execute(request)

        
        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()
        MockUser.validate_password.assert_called_once_with("short")
        mock_password_hasher.hash.assert_not_called()
        MockUser.create.assert_not_called()

    async def test_user_creation_failure(
        self,
        use_case,
        mock_uow,
        mock_password_hasher,
        sample_email,
        sample_password,
    ):
        
        
        mock_uow.users.get_by_email = AsyncMock(return_value=None)
        request = RegisterUserRequest(email=sample_email, password=sample_password)

        with patch('src.application.use_cases.register_user.User') as MockUser:
            MockUser.validate_password = Mock()
            MockUser.create = Mock(side_effect=ValueError("Some validation error"))
            
            with pytest.raises(ValidationError):
                await use_case.execute(request)

        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()
        MockUser.validate_password.assert_called_once_with(sample_password)
        mock_password_hasher.hash.assert_called_once_with(sample_password)