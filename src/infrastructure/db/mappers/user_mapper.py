from ....domain.entities.user import User
from ..models.user import UserModel


def user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        created_at=user.created_at,
    )


def model_to_user(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        created_at=model.created_at,
    )