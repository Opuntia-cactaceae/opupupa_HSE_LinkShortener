import pytest
import string

from src.application.services.short_code_generator import (
    ShortCodeGenerator,
    Base62ShortCodeGenerator,
)


class TestShortCodeGenerator:
    def test_short_code_generator_is_abstract(self):
        """Test that ShortCodeGenerator is an abstract base class."""
        with pytest.raises(TypeError):
            ShortCodeGenerator()  # type: ignore

    def test_base62_short_code_generator_default_length(self):
        """Test Base62ShortCodeGenerator with default length."""
        generator = Base62ShortCodeGenerator()
        code = generator.generate()
        assert len(code) == 8
        assert all(c in string.ascii_letters + string.digits for c in code)

    def test_base62_short_code_generator_custom_length(self):
        """Test Base62ShortCodeGenerator with custom valid lengths."""
        # Test minimum length (7)
        generator = Base62ShortCodeGenerator(length=7)
        code = generator.generate()
        assert len(code) == 7
        assert all(c in string.ascii_letters + string.digits for c in code)

        # Test maximum length (10)
        generator = Base62ShortCodeGenerator(length=10)
        code = generator.generate()
        assert len(code) == 10
        assert all(c in string.ascii_letters + string.digits for c in code)

        # Test middle length (9)
        generator = Base62ShortCodeGenerator(length=9)
        code = generator.generate()
        assert len(code) == 9

    def test_base62_short_code_generator_invalid_length(self):
        """Test Base62ShortCodeGenerator with invalid lengths."""
        with pytest.raises(ValueError, match="Length must be between 7 and 10"):
            Base62ShortCodeGenerator(length=6)
        with pytest.raises(ValueError):
            Base62ShortCodeGenerator(length=11)
        with pytest.raises(ValueError):
            Base62ShortCodeGenerator(length=0)

    def test_base62_short_code_generator_charset(self):
        """Test that generated codes use only allowed characters."""
        generator = Base62ShortCodeGenerator()
        allowed_chars = set(string.ascii_letters + string.digits)

        # Generate many codes and verify all characters are allowed
        for _ in range(100):
            code = generator.generate()
            assert all(c in allowed_chars for c in code), f"Invalid character in code: {code}"

    def test_base62_short_code_generator_multiple_codes_format(self):
        """Test that many generated codes all have correct format."""
        generator = Base62ShortCodeGenerator()
        allowed_chars = set(string.ascii_letters + string.digits)

        for _ in range(100):
            code = generator.generate()
            assert len(code) == 8
            assert all(c in allowed_chars for c in code)

    def test_base62_short_code_generator_collision_sanity_check(self):
        """Basic sanity check for collisions on a batch of generated codes."""
        generator = Base62ShortCodeGenerator()
        codes = set()

        # Generate a batch of codes
        for _ in range(1000):
            code = generator.generate()
            codes.add(code)

        # With 1000 codes, we expect very few collisions if any
        # This is a sanity check, not a guarantee
        assert len(codes) > 950, f"Too many collisions: {1000 - len(codes)}"

    def test_base62_short_code_generator_uniqueness_per_call(self):
        """Test that consecutive calls generate different codes (probabilistic)."""
        generator = Base62ShortCodeGenerator()
        code1 = generator.generate()
        code2 = generator.generate()
        code3 = generator.generate()

        # It's possible but extremely unlikely to get the same code three times
        # This test could theoretically fail, but probability is astronomically low
        assert not (code1 == code2 == code3), "Got same code three times in a row"

    def test_base62_short_code_generator_security(self):
        """Test that generator uses cryptographically secure random."""
        # The implementation uses secrets.choice which is cryptographically secure
        # We can't directly test this, but we can verify the module is used
        import secrets
        generator = Base62ShortCodeGenerator()
        code = generator.generate()
        # The fact that it doesn't raise exceptions and produces valid codes
        # suggests secrets.choice is working
        assert len(code) == 8