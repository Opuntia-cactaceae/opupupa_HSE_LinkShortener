import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt
from src.domain.entities.link import Link


class TestLink:
    def setup_method(self):
        self.short_code = ShortCode("test123")
        self.original_url = OriginalUrl("https://example.com")
        self.user_id = uuid4()
        self.future_date = datetime.now(timezone.utc) + timedelta(days=1)
        self.past_date = datetime.now(timezone.utc) - timedelta(days=1)

    def test_create_link_with_owner(self):
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        assert link.short_code == self.short_code
        assert link.original_url == self.original_url
        assert link.owner_user_id == self.user_id
        assert link.expires_at is None
        assert link.project_id is None
        assert link.expired_at is None
        assert not link.is_deleted
        assert isinstance(link.id, UUID)
        assert link.created_at is not None

    def test_create_anonymous_link(self):
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=None,
        )
        assert link.owner_user_id is None
        assert link.is_owner(None) is True
        assert link.is_owner(self.user_id) is False

    def test_create_link_with_expiration(self):
        expires_at = ExpiresAt.from_datetime(self.future_date)
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            expires_at=expires_at,
        )
        assert link.expires_at == expires_at
        assert not link.is_expired(self.future_date - timedelta(hours=1))
        assert link.is_expired(self.future_date + timedelta(hours=1))

    def test_create_link_with_project(self):
        project_id = uuid4()
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            project_id=project_id,
        )
        assert link.project_id == project_id

    def test_is_owner(self):
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        assert link.is_owner(self.user_id) is True
        assert link.is_owner(uuid4()) is False
        assert link.is_owner(None) is False

    def test_is_owner_anonymous_link(self):
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=None,
        )
        assert link.is_owner(None) is True
        assert link.is_owner(self.user_id) is False

    def test_is_expired_with_expiration_date(self):
        expires_at = ExpiresAt.from_datetime(self.future_date)
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            expires_at=expires_at,
        )
        
        assert not link.is_expired(self.future_date - timedelta(hours=1))
        assert link.is_expired(self.future_date + timedelta(hours=1))

    def test_is_expired_without_expiration_date(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        assert not link.is_expired(self.future_date)
        assert not link.is_expired(self.past_date)

    def test_is_expired_when_marked_expired(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        expired_at = datetime.now(timezone.utc)
        link.mark_expired(expired_at)
        assert link.expired_at == expired_at
        assert link.is_expired(expired_at)
        assert link.is_expired(expired_at + timedelta(hours=1))

    def test_is_available(self):
        
        expires_at = ExpiresAt.from_datetime(self.future_date)
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            expires_at=expires_at,
        )
        
        assert link.is_available(self.future_date - timedelta(hours=1)) is True
        assert link.is_available(self.future_date + timedelta(hours=1)) is False
        link.delete()
        assert link.is_available(self.future_date - timedelta(hours=1)) is False
        link.restore()
        assert link.is_available(self.future_date - timedelta(hours=1)) is True

    def test_update_original_url(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        new_url = OriginalUrl("https://new-example.com")
        original_updated_at = link.updated_at

        link.update_original_url(new_url)
        assert link.original_url == new_url
        assert link.updated_at > original_updated_at

    def test_update_short_code(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        new_short_code = ShortCode("newcode456")
        original_updated_at = link.updated_at

        link.update_short_code(new_short_code)
        assert link.short_code == new_short_code
        assert link.updated_at > original_updated_at

    def test_update_expires_at(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        new_expires_at = ExpiresAt.from_datetime(self.future_date + timedelta(days=2))
        original_updated_at = link.updated_at

        link.update_expires_at(new_expires_at)
        assert link.expires_at == new_expires_at
        assert link.updated_at > original_updated_at

        
        link.update_expires_at(None)
        assert link.expires_at is None

    def test_update_project_id(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        new_project_id = uuid4()
        original_updated_at = link.updated_at

        link.update_project_id(new_project_id)
        assert link.project_id == new_project_id
        assert link.updated_at > original_updated_at
        
        link.update_project_id(None)
        assert link.project_id is None

    def test_mark_expired(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        expired_at = datetime.now(timezone.utc)
        original_updated_at = link.updated_at

        link.mark_expired(expired_at)
        assert link.expired_at == expired_at
        assert link.updated_at > original_updated_at
        assert link.is_expired(expired_at) is True

    def test_delete_and_restore(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        original_updated_at = link.updated_at

        link.delete()
        assert link.is_deleted is True
        assert link.updated_at > original_updated_at
        assert link.is_available(datetime.now(timezone.utc)) is False

        link.restore()
        assert link.is_deleted is False
        assert link.is_available(datetime.now(timezone.utc)) is True

    def test_link_immutable_properties(self):
        
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        
        with pytest.raises(AttributeError):
            link.short_code = ShortCode("modified")  
        with pytest.raises(AttributeError):
            link.original_url = OriginalUrl("https://modified.com")  

    def test_link_equality(self):
        
        link1 = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        link2 = Link.create(
            short_code=ShortCode("other"),
            original_url=OriginalUrl("https://other.com"),
            owner_user_id=uuid4(),
        )
        assert link1 != link2
        assert link1 == link1