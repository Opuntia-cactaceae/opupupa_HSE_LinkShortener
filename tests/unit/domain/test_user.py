import pytest
from uuid import UUID
from unittest.mock import patch

from src.domain.entities.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")



class TestUser:
    def test_create_user(self):
        """Test creating a user with valid email and password."""
        with patch('tests.unit.domain.test_user.pwd_context.hash') as mock_hash:
            mock_hash.return_value = "hashed_password"
            password_hash = pwd_context.hash("password")
            user = User.create("test@example.com", password_hash)
            assert user.email == "test@example.com"
            assert user.password_hash is not None
            assert isinstance(user.id, UUID)
            assert user.created_at is not None

    def test_create_user_normalizes_email(self):
        """Test that email is normalized to lowercase."""
        password_hash = pwd_context.hash("password")
        user = User.create("Test@Example.COM", password_hash)
        assert user.email == "test@example.com"

    def test_create_user_with_whitespace_email(self):
        """Test that email whitespace is trimmed."""
        password_hash = pwd_context.hash("password")
        user = User.create("  test@example.com  ", password_hash)
        assert user.email == "test@example.com"

    def test_create_user_invalid_email(self):
        """Test that invalid email raises error."""
        password_hash = pwd_context.hash("password")
        with pytest.raises(ValueError, match="Invalid email format"):
            User.create("invalid-email", password_hash)
        with pytest.raises(ValueError):
            User.create("test@", password_hash)
        with pytest.raises(ValueError):
            User.create("@example.com", password_hash)
        with pytest.raises(ValueError):
            User.create("test@example", password_hash)

    def test_create_user_password_too_short(self):
        """Test that password less than 8 characters raises error."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            User.validate_password("short")
        with pytest.raises(ValueError):
            User.validate_password("")


    def test_user_immutable_properties(self):
        """Test that user properties are immutable."""
        password_hash = pwd_context.hash("password")
        user = User.create("test@example.com", password_hash)
        # Should not be able to modify email or password_hash directly
        with pytest.raises(AttributeError):
            user.email = "modified@example.com"  # type: ignore
        with pytest.raises(AttributeError):
            user.password_hash = "modified"  # type: ignore

    def test_user_equality(self):
        """Test that User instances with same ID are equal."""
        password_hash1 = pwd_context.hash("password")
        password_hash2 = pwd_context.hash("password456")
        user1 = User.create("test1@example.com", password_hash1)
        user2 = User.create("test2@example.com", password_hash2)
        # Users with different IDs should not be equal
        assert user1 != user2
        # User should equal itself
        assert user1 == user1

    def test_direct_instantiation(self):
        """Test creating user directly with password hash."""
        # Create a user via the factory method to get a valid hash
        temp_hash = pwd_context.hash("password")
        temp_user = User.create("temp@example.com", temp_hash)
        password_hash = temp_user.password_hash

        # Create user directly with the same hash
        user = User("test@example.com", password_hash)
        assert user.email == "test@example.com"
        assert user.password_hash == password_hash

    def test_user_with_existing_id(self):
        """Test creating user with existing ID."""
        from uuid import uuid4
        user_id = uuid4()
        # Create a user via the factory method to get a valid hash
        temp_hash = pwd_context.hash("password")
        temp_user = User.create("temp@example.com", temp_hash)
        password_hash = temp_user.password_hash

        user = User("test@example.com", password_hash, id=user_id)
        assert user.id == user_id