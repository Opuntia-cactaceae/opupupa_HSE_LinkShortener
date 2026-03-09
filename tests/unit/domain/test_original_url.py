import pytest

from src.domain.value_objects.original_url import OriginalUrl


class TestOriginalUrl:
    def test_valid_http_url(self):
        """Test creating a valid HTTP URL."""
        url = OriginalUrl("http://example.com")
        assert str(url) == "http://example.com"
        assert url.value == "http://example.com"

    def test_valid_https_url(self):
        """Test creating a valid HTTPS URL."""
        url = OriginalUrl("https://example.com")
        assert str(url) == "https://example.com"

    def test_valid_url_with_path(self):
        """Test URL with path, query, and fragment."""
        url = OriginalUrl("https://example.com/path/to/page?query=value#section")
        assert str(url) == "https://example.com/path/to/page?query=value#section"

    def test_valid_url_with_port(self):
        """Test URL with port number."""
        url = OriginalUrl("https://example.com:8080/path")
        assert str(url) == "https://example.com:8080/path"

    def test_url_empty(self):
        """Test that empty URL raises error."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            OriginalUrl("")

    def test_url_missing_scheme(self):
        """Test URL without scheme raises error."""
        with pytest.raises(ValueError, match="URL must have a scheme"):
            OriginalUrl("example.com")

    def test_url_invalid_scheme(self):
        """Test URL with invalid scheme (not http or https) raises error."""
        with pytest.raises(ValueError, match="URL scheme must be http or https"):
            OriginalUrl("ftp://example.com")
        with pytest.raises(ValueError):
            OriginalUrl("file:///path/to/file")

    def test_url_missing_host(self):
        """Test URL without hostname raises error."""
        with pytest.raises(ValueError, match="URL must have a hostname"):
            OriginalUrl("http://")
        with pytest.raises(ValueError):
            OriginalUrl("https:///path")

    def test_url_too_long(self):
        """Test that URL exceeding maximum length raises error."""
        long_url = "https://example.com/" + "a" * 2000
        with pytest.raises(ValueError, match="URL is too long"):
            OriginalUrl(long_url)

    def test_url_max_length_allowed(self):
        """Test URL at maximum allowed length."""
        # Create a URL that's exactly 2000 characters
        base = "https://example.com/"
        remaining = 2000 - len(base)
        long_path = "a" * remaining
        url = OriginalUrl(base + long_path)
        assert len(url.value) == 2000

    def test_from_string_factory_method(self):
        """Test the from_string class method."""
        url = OriginalUrl.from_string("https://example.com")
        assert isinstance(url, OriginalUrl)
        assert url.value == "https://example.com"

    def test_url_is_immutable(self):
        """Test that OriginalUrl is immutable (frozen dataclass)."""
        url = OriginalUrl("https://example.com")
        with pytest.raises(AttributeError):
            url.value = "http://modified.com"  # type: ignore

    def test_url_equality(self):
        """Test that OriginalUrl instances with same value are equal."""
        url1 = OriginalUrl("https://example.com")
        url2 = OriginalUrl("https://example.com")
        url3 = OriginalUrl("https://different.com")
        assert url1 == url2
        assert url1 != url3
        assert hash(url1) == hash(url2)

