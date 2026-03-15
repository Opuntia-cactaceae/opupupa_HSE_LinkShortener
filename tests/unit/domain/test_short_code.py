import pytest

from src.domain.value_objects.short_code import ShortCode


class TestShortCode:
    def test_valid_short_code(self):
        code = ShortCode("abc123")
        assert str(code) == "abc123"
        assert code.value == "abc123"

    def test_valid_short_code_with_hyphen_underscore(self):
        code = ShortCode("a-b_c123")
        assert str(code) == "a-b_c123"

    def test_short_code_min_length(self):
        code = ShortCode("abc")
        assert str(code) == "abc"

    def test_short_code_max_length(self):
        code = ShortCode("a" * 32)
        assert len(code.value) == 32

    def test_short_code_empty(self):
        with pytest.raises(ValueError, match="Short code cannot be empty"):
            ShortCode("")

    def test_short_code_too_short(self):
        with pytest.raises(ValueError, match="Short code must be at least 3 characters"):
            ShortCode("a")

    def test_short_code_too_long(self):
        with pytest.raises(ValueError, match="Short code cannot exceed 32 characters"):
            ShortCode("a" * 33)

    def test_short_code_invalid_characters(self):
        with pytest.raises(ValueError, match="Short code can only contain letters, numbers, hyphens and underscores"):
            ShortCode("abc@123")
        with pytest.raises(ValueError):
            ShortCode("abc 123")
        with pytest.raises(ValueError):
            ShortCode("abc.123")
        with pytest.raises(ValueError):
            ShortCode("abc/123")

    def test_from_string_factory_method(self):
        code = ShortCode.from_string("test123")
        assert isinstance(code, ShortCode)
        assert code.value == "test123"

    def test_short_code_is_immutable(self):
        code = ShortCode("test123")
        with pytest.raises(AttributeError):
            code.value = "modified"  #бесит вот это выделение в айдеешке, я же блин его же тесчу

    def test_short_code_equality(self):
        code1 = ShortCode("test123")
        code2 = ShortCode("test123")
        code3 = ShortCode("different")
        assert code1 == code2
        assert code1 != code3
        assert hash(code1) == hash(code2)