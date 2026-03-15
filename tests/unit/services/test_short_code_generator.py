import pytest
import string

from src.application.services.short_code_generator import (
    ShortCodeGenerator,
    Base62ShortCodeGenerator,
)


class TestShortCodeGenerator:
    def test_short_code_generator_is_abstract(self):
        
        with pytest.raises(TypeError):
            ShortCodeGenerator()  

    def test_base62_short_code_generator_default_length(self):
        
        generator = Base62ShortCodeGenerator()
        code = generator.generate()
        assert len(code) == 8
        assert all(c in string.ascii_letters + string.digits for c in code)

    def test_base62_short_code_generator_custom_length(self):
        
        generator = Base62ShortCodeGenerator(length=7)
        code = generator.generate()
        assert len(code) == 7
        assert all(c in string.ascii_letters + string.digits for c in code)
        
        generator = Base62ShortCodeGenerator(length=10)
        code = generator.generate()
        assert len(code) == 10
        assert all(c in string.ascii_letters + string.digits for c in code)
        
        generator = Base62ShortCodeGenerator(length=9)
        code = generator.generate()
        assert len(code) == 9

    def test_base62_short_code_generator_invalid_length(self):
        
        with pytest.raises(ValueError, match="Length must be between 7 and 10"):
            Base62ShortCodeGenerator(length=6)
        with pytest.raises(ValueError):
            Base62ShortCodeGenerator(length=11)
        with pytest.raises(ValueError):
            Base62ShortCodeGenerator(length=0)

    def test_base62_short_code_generator_charset(self):
        
        generator = Base62ShortCodeGenerator()
        allowed_chars = set(string.ascii_letters + string.digits)

        for _ in range(100):
            code = generator.generate()
            assert all(c in allowed_chars for c in code), f"Invalid character in code: {code}"

    def test_base62_short_code_generator_multiple_codes_format(self):
        
        generator = Base62ShortCodeGenerator()
        allowed_chars = set(string.ascii_letters + string.digits)

        for _ in range(100):
            code = generator.generate()
            assert len(code) == 8
            assert all(c in allowed_chars for c in code)

    def test_base62_short_code_generator_collision_sanity_check(self):
        
        generator = Base62ShortCodeGenerator()
        codes = set()

        for _ in range(1000):
            code = generator.generate()
            codes.add(code)

        assert len(codes) > 950, f"Too many collisions: {1000 - len(codes)}"

    def test_base62_short_code_generator_uniqueness_per_call(self):
        
        generator = Base62ShortCodeGenerator()
        code1 = generator.generate()
        code2 = generator.generate()
        code3 = generator.generate()

        assert not (code1 == code2 == code3), "Got same code three times in a row"

    def test_base62_short_code_generator_security(self):
        import secrets
        generator = Base62ShortCodeGenerator()
        code = generator.generate()
        
        
        assert len(code) == 8