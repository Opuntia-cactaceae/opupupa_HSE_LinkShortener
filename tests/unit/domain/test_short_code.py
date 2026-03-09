import pytest

from src.domain.value_objects.short_code import ShortCode


class TestShortCode:
    def test_valid_short_code(self):
        """Test creating a valid short code."""
        code = ShortCode("abc123")
        assert str(code) == "abc123"
        assert code.value == "abc123"

    def test_valid_short_code_with_hyphen_underscore(self):
        """Test short code with hyphens and underscores."""
        code = ShortCode("a-b_c123")
        assert str(code) == "a-b_c123"

    def test_short_code_min_length(self):
        """Test short code with minimum allowed length (3 characters)."""
        code = ShortCode("abc")
        assert str(code) == "abc"

    def test_short_code_max_length(self):
        """Test short code with maximum allowed length (32 characters)."""
        code = ShortCode("a" * 32)
        assert len(code.value) == 32

    def test_short_code_empty(self):
        """Test that empty short code raises error."""
        with pytest.raises(ValueError, match="Short code cannot be empty"):
            ShortCode("")

    def test_short_code_too_short(self):
        """Test that short code less than 3 characters raises error."""
        with pytest.raises(ValueError, match="Short code must be at least 3 characters"):
            ShortCode("a")

    def test_short_code_too_long(self):
        """Test that short code more than 32 characters raises error."""
        with pytest.raises(ValueError, match="Short code cannot exceed 32 characters"):
            ShortCode("a" * 33)

    def test_short_code_invalid_characters(self):
        """Test that short code with invalid characters raises error."""
        with pytest.raises(ValueError, match="Short code can only contain letters, numbers, hyphens and underscores"):
            ShortCode("abc@123")
        with pytest.raises(ValueError):
            ShortCode("abc 123")
        with pytest.raises(ValueError):
            ShortCode("abc.123")
        with pytest.raises(ValueError):
            ShortCode("abc/123")

    def test_from_string_factory_method(self):
        """Test the from_string class method."""
        code = ShortCode.from_string("test123")
        assert isinstance(code, ShortCode)
        assert code.value == "test123"

    def test_short_code_is_immutable(self):
        """Test that ShortCode is immutable (frozen dataclass)."""
        code = ShortCode("test123")
        with pytest.raises(AttributeError):
            code.value = "modified"  # type: ignore

    def test_short_code_equality(self):
        """Test that ShortCode instances with same value are equal."""
        code1 = ShortCode("test123")
        code2 = ShortCode("test123")
        code3 = ShortCode("different")
        assert code1 == code2
        assert code1 != code3
        assert hash(code1) == hash(code2)