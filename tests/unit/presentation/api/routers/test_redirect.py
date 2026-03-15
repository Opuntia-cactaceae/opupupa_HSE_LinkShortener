import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi.responses import RedirectResponse

from src.presentation.api.routers.redirect import redirect_to_original


class TestRedirectRouter:
    

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def mock_uow(self):
        return AsyncMock()

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.DEFAULT_CACHE_TTL_SEC = 300
        return settings

    @pytest.fixture
    def mock_resolve_link_result(self):
        result = MagicMock()
        result.original_url = "https://example.com"
        result.expires_at = None
        result.link_id = "some-id"
        return result

    @pytest.fixture
    def mock_time_provider(self):
        provider = MagicMock()
        provider.now.return_value = datetime.now(timezone.utc)
        return provider

    async def test_redirect_cache_hit_no_expiration(self, mock_cache, mock_uow, mock_settings, mock_resolve_link_result, mock_time_provider):
        
        short_code = "abc123"
        mock_cache.get.return_value = {
            "original_url": "https://cached.example.com",
            "expires_at": None,
            "link_id": "cached-id"
        }
        
        with patch('src.presentation.api.routers.redirect.SystemTimeProvider') as mock_system_time:
            mock_system_time.return_value = mock_time_provider
            with patch('src.presentation.api.routers.redirect.ResolveLinkUseCase') as mock_use_case_class:
                mock_use_case = AsyncMock()
                mock_use_case.execute = AsyncMock(return_value=mock_resolve_link_result)
                mock_use_case_class.return_value = mock_use_case
                
                response = await redirect_to_original(
                    short_code=short_code,
                    cache=mock_cache,
                    uow=mock_uow,
                    settings=mock_settings
                )

        
        mock_cache.get.assert_called_once_with(short_code)
        
        mock_use_case.execute.assert_called_once_with(short_code)
        
        mock_cache.set.assert_not_called()
        
        assert isinstance(response, RedirectResponse)
        assert response.headers['Location'] == mock_resolve_link_result.original_url
        assert response.status_code == 307

    async def test_redirect_cache_miss(self, mock_cache, mock_uow, mock_settings, mock_resolve_link_result, mock_time_provider):
        
        short_code = "abc123"
        mock_cache.get.return_value = None
        with patch('src.presentation.api.routers.redirect.SystemTimeProvider') as mock_system_time:
            mock_system_time.return_value = mock_time_provider
            with patch('src.presentation.api.routers.redirect.ResolveLinkUseCase') as mock_use_case_class:
                mock_use_case = AsyncMock()
                mock_use_case.execute = AsyncMock(return_value=mock_resolve_link_result)
                mock_use_case_class.return_value = mock_use_case
                response = await redirect_to_original(
                    short_code=short_code,
                    cache=mock_cache,
                    uow=mock_uow,
                    settings=mock_settings
                )

        mock_cache.get.assert_called_once_with(short_code)
        mock_use_case.execute.assert_called_once_with(short_code)
        
        mock_cache.set.assert_called_once_with(
            short_code=short_code,
            original_url=mock_resolve_link_result.original_url,
            expires_at=mock_resolve_link_result.expires_at,
            link_id=mock_resolve_link_result.link_id,
            ttl_sec=mock_settings.DEFAULT_CACHE_TTL_SEC,
        )
        assert isinstance(response, RedirectResponse)
        assert response.headers['Location'] == mock_resolve_link_result.original_url

    async def test_redirect_cache_expired(self, mock_cache, mock_uow, mock_settings, mock_resolve_link_result, mock_time_provider):
        
        short_code = "abc123"
        expired_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) - timedelta(seconds=3600)
        mock_cache.get.return_value = {
            "original_url": "https://expired.example.com",
            "expires_at": expired_time.isoformat(),
            "link_id": "expired-id"
        }
        with patch('src.presentation.api.routers.redirect.SystemTimeProvider') as mock_system_time:
            mock_system_time.return_value = mock_time_provider
            with patch('src.presentation.api.routers.redirect.ResolveLinkUseCase') as mock_use_case_class:
                mock_use_case = AsyncMock()
                mock_use_case.execute = AsyncMock(return_value=mock_resolve_link_result)
                mock_use_case_class.return_value = mock_use_case
                response = await redirect_to_original(
                    short_code=short_code,
                    cache=mock_cache,
                    uow=mock_uow,
                    settings=mock_settings
                )

        mock_cache.get.assert_called_once_with(short_code)
        mock_use_case.execute.assert_called_once_with(short_code)
        
        mock_cache.set.assert_called_once_with(
            short_code=short_code,
            original_url=mock_resolve_link_result.original_url,
            expires_at=mock_resolve_link_result.expires_at,
            link_id=mock_resolve_link_result.link_id,
            ttl_sec=mock_settings.DEFAULT_CACHE_TTL_SEC,
        )
        assert isinstance(response, RedirectResponse)

    async def test_redirect_cache_hit_with_expiration_future(self, mock_cache, mock_uow, mock_settings, mock_resolve_link_result, mock_time_provider):
        
        short_code = "abc123"
        future_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
        mock_cache.get.return_value = {
            "original_url": "https://cached.example.com",
            "expires_at": future_time.isoformat(),
            "link_id": "cached-id"
        }
        with patch('src.presentation.api.routers.redirect.SystemTimeProvider') as mock_system_time:
            mock_system_time.return_value = mock_time_provider
            with patch('src.presentation.api.routers.redirect.ResolveLinkUseCase') as mock_use_case_class:
                mock_use_case = AsyncMock()
                mock_use_case.execute = AsyncMock(return_value=mock_resolve_link_result)
                mock_use_case_class.return_value = mock_use_case
                response = await redirect_to_original(
                    short_code=short_code,
                    cache=mock_cache,
                    uow=mock_uow,
                    settings=mock_settings
                )

        mock_cache.get.assert_called_once_with(short_code)
        mock_use_case.execute.assert_called_once_with(short_code)
        
        mock_cache.set.assert_not_called()
        assert isinstance(response, RedirectResponse)

    async def test_redirect_cache_hit_expires_at_no_tzinfo(self, mock_cache, mock_uow, mock_settings, mock_resolve_link_result, mock_time_provider):
        
        short_code = "abc123"
        future_time = datetime.now(timezone.utc) + timedelta(seconds=3600)
        
        future_naive = future_time.replace(tzinfo=None)
        mock_cache.get.return_value = {
            "original_url": "https://cached.example.com",
            "expires_at": future_naive.isoformat(),
            "link_id": "cached-id"
        }
        with patch('src.presentation.api.routers.redirect.SystemTimeProvider') as mock_system_time:
            mock_system_time.return_value = mock_time_provider
            with patch('src.presentation.api.routers.redirect.ResolveLinkUseCase') as mock_use_case_class:
                mock_use_case = AsyncMock()
                mock_use_case.execute = AsyncMock(return_value=mock_resolve_link_result)
                mock_use_case_class.return_value = mock_use_case
                response = await redirect_to_original(
                    short_code=short_code,
                    cache=mock_cache,
                    uow=mock_uow,
                    settings=mock_settings
                )

        mock_cache.set.assert_not_called()
        assert isinstance(response, RedirectResponse)