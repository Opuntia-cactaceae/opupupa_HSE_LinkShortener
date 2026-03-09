from ..dto.auth_dto import AuthResponse, LoginUserRequest
from ..errors.errors import InvalidCredentialsError, UserNotFoundError
from ..services.password_hasher import PasswordHasher
from ..services.token_provider import TokenProvider
from ...domain.repositories.unit_of_work import IUnitOfWork


class LoginUserUseCase:
    def __init__(self, uow: IUnitOfWork, password_hasher: PasswordHasher, token_provider: TokenProvider) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._token_provider = token_provider

    async def execute(self, request: LoginUserRequest) -> AuthResponse:
        user = await self._uow.users.get_by_email(request.email)
        if user is None:
            raise UserNotFoundError()

        if not self._password_hasher.verify(request.password, user.password_hash):
            raise InvalidCredentialsError()

        token = self._token_provider.encode(user.id)
        return AuthResponse(access_token=token)