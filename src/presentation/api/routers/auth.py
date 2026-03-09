from fastapi import APIRouter, Depends, status

from ...schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
)
from ....application.dto.auth_dto import LoginUserRequest, RegisterUserRequest
from ....application.use_cases.login_user import LoginUserUseCase
from ....application.use_cases.register_user import RegisterUserUseCase
from ..deps import (
    get_password_hasher,
    get_token_provider,
    get_uow,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    uow=Depends(get_uow),
    password_hasher=Depends(get_password_hasher),
) -> RegisterResponse:
    dto_request = RegisterUserRequest(
        email=request.email,
        password=str(request.password),
    )
    use_case = RegisterUserUseCase(uow, password_hasher)
    dto_response = await use_case.execute(dto_request)
    return RegisterResponse.from_dto(dto_response)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    uow=Depends(get_uow),
    password_hasher=Depends(get_password_hasher),
    token_provider=Depends(get_token_provider),
) -> AuthResponse:
    dto_request = LoginUserRequest(
        email=request.email,
        password=str(request.password),
    )
    use_case = LoginUserUseCase(uow, password_hasher, token_provider)
    dto_response = await use_case.execute(dto_request)
    return AuthResponse.from_dto(dto_response)