from ...domain.entities.user import User
from ..dto.auth_dto import RegisterUserRequest, RegisterUserResponse
from ..errors.errors import EmailAlreadyExistsError, ValidationError
from ...domain.repositories.unit_of_work import IUnitOfWork
from ..services.password_hasher import PasswordHasher


class RegisterUserUseCase:
    def __init__(self, uow: IUnitOfWork, password_hasher: PasswordHasher) -> None:
        self._uow = uow
        self._password_hasher = password_hasher

    async def execute(self, request: RegisterUserRequest) -> RegisterUserResponse:
        existing_user = await self._uow.users.get_by_email(request.email)
        if existing_user is not None:
            raise EmailAlreadyExistsError()

        try:
            User.validate_password(request.password)
            password_hash = self._password_hasher.hash(request.password)
            user = User.create(request.email, password_hash)
        except ValueError as e:
            raise ValidationError(str(e))

        await self._uow.users.add(user)
        await self._uow.commit()

        return RegisterUserResponse(user_id=user.id)