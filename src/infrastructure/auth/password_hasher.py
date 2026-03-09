import bcrypt

from ...application.services.password_hasher import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except ValueError:
            return False