import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call
from uuid import uuid4


class TestCacheBehaviour:
    """
        Тут на самом деле просто база для редиректов:
        - при отсутствии записи в Redis ссылка берётся из БД и сохраняется в кэш;
        - при наличии записи данные используются из кэша без повторной записи;
        - кэш очищается при обновлении ссылки;
        - кэш очищается при изменении кода;
        - кэш очищается при удалении ссылки;
        - кэш очищается при удалении истёкших ссылок.
        """
    @pytest.mark.asyncio
    async def test_redirect_cache_miss_db_fetch_cache_set(
        self, client, redis_client, uow, test_settings
    ):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "cachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]

        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        assert response.status_code == 307

        redis_client.client.get.assert_called_once_with(f"link:code:{short_code}")

        assert redis_client.client.setex.call_count == 1
        setex_call = redis_client.client.setex.call_args
        assert setex_call[0][0] == f"link:code:{short_code}"

        assert setex_call[0][1] == test_settings.DEFAULT_CACHE_TTL_SEC

        cached_data = json.loads(setex_call[0][2])
        assert cached_data["original_url"] == original_url

        assert "link_id" in cached_data

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_no_cache_set(self, client, redis_client, uow):


        payload = {
            "original_url": "https://example.com",
            "custom_alias": "cachehittest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]

        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        assert redis_client.client.setex.call_count == 1
        setex_call = redis_client.client.setex.call_args
        cached_json = setex_call[0][2]

        redis_client.client.get.return_value = cached_json

        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        assert response.status_code == 307

        redis_client.client.get.assert_called_once_with(f"link:code:{short_code}")

        redis_client.client.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_update(self, client, redis_client, uow, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "updatecachetest"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        redis_client.client.delete.reset_mock()

        update_payload = {
            "original_url": "https://updated-example.com"
        }
        response = await client.put(
            f"/links/{short_code}",
            json=update_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_update_with_new_short_code(
            self, client, redis_client, uow, auth_headers
    ):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "updatealias"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        redis_client.client.delete.reset_mock()

        new_alias = "newalias"
        update_payload = {
            "new_short_code": new_alias
        }
        response = await client.put(
            f"/links/{short_code}",
            json=update_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

        assert redis_client.client.delete.call_count == 2
        delete_calls = redis_client.client.delete.call_args_list
        delete_keys = [call[0][0] for call in delete_calls]
        assert f"link:code:{short_code}" in delete_keys
        assert f"link:code:{new_alias}" in delete_keys

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_delete(
            self,
            client,
            redis_client,
            uow,
            auth_headers,
    ):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "deletecachetest"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        redis_client.client.delete.reset_mock()

        response = await client.delete(f"/links/{short_code}", headers=auth_headers)
        assert response.status_code == 204

        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")

    @pytest.mark.asyncio
    async def test_cache_invalidated_after_purge_job(
        self, client, redis_client, uow, test_settings
    ):

        payload = {
            "original_url": "https://example.com",
            "custom_alias": "purgecachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        redis_client.client.delete.reset_mock()

        async with uow:
            link = await uow.links.get_by_short_code(short_code)
            past_time = datetime.now(timezone.utc).replace(microsecond=0)
            from src.domain.value_objects.expires_at import ExpiresAt
            link.update_expires_at(ExpiresAt.from_datetime(past_time))
            await uow.links.update(link)
            await uow.commit()

        from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob
        from src.infrastructure.cache.link_cache import LinkCache

        cache = LinkCache()
        cache._redis = redis_client

        job = PurgeExpiredLinksJob(
            uow_factory=lambda: uow,
            cache=cache,
            interval_sec=3600,
        )

        redis_client.client.delete.reset_mock()

        await job._purge_batch()

        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")