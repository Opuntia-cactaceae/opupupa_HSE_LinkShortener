import pytest
from uuid import UUID

from src.domain.entities.user import User


def fake_hash(password: str) -> str:
    return f"hashed_{password}"


class TestUser:
    def test_create_user(self):
        password_hash = fake_hash("password")
        user = User.create("test@example.com", password_hash)
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert isinstance(user.id, UUID)
        assert user.created_at is not None

    def test_create_user_normalizes_email(self):
        password_hash = fake_hash("password")
        user = User.create("Test@Example.COM", password_hash)
        assert user.email == "test@example.com"

    def test_create_user_with_whitespace_email(self):
        password_hash = fake_hash("password")
        user = User.create("  test@example.com  ", password_hash)
        assert user.email == "test@example.com"

    def test_create_user_invalid_email(self):
        password_hash = fake_hash("password")
        with pytest.raises(ValueError, match="Invalid email format"):
            User.create("invalid-email", password_hash)
        with pytest.raises(ValueError):
            User.create("test@", password_hash)
        with pytest.raises(ValueError):
            User.create("@example.com", password_hash)
        with pytest.raises(ValueError):
            User.create("test@example", password_hash)

    def test_create_user_password_too_short(self):
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            User.validate_password("short")
        with pytest.raises(ValueError):
            User.validate_password("")

    def test_user_immutable_properties(self):
        password_hash = fake_hash("password")
        user = User.create("test@example.com", password_hash)
        
        with pytest.raises(AttributeError):
            user.email = "modified@example.com"  
        with pytest.raises(AttributeError):
            user.password_hash = "modified"  

    def test_user_equality(self):
        password_hash1 = fake_hash("password")
        password_hash2 = fake_hash("password456")
        user1 = User.create("test1@example.com", password_hash1)
        user2 = User.create("test2@example.com", password_hash2)
        
        assert user1 != user2
        
        assert user1 == user1

    def test_direct_instantiation(self):
        temp_hash = fake_hash("password")
        temp_user = User.create("temp@example.com", temp_hash)
        password_hash = temp_user.password_hash

        user = User("test@example.com", password_hash)
        assert user.email == "test@example.com"
        assert user.password_hash == password_hash

    def test_user_with_existing_id(self):
        from uuid import uuid4
        user_id = uuid4()
        
        temp_hash = fake_hash("password")
        temp_user = User.create("temp@example.com", temp_hash)
        password_hash = temp_user.password_hash

        user = User("test@example.com", password_hash, id=user_id)
        assert user.id == user_id