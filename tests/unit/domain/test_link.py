import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt
from src.domain.entities.link import Link


class TestLink:
    def setup_method(self):
        """Setup common test data."""
        self.short_code = ShortCode("test123")
        self.original_url = OriginalUrl("https://example.com")
        self.user_id = uuid4()
        self.future_date = datetime.now(timezone.utc) + timedelta(days=1)
        self.past_date = datetime.now(timezone.utc) - timedelta(days=1)

    def test_create_link_with_owner(self):
        """Test creating a link with an owner."""
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
        """Test creating an anonymous link (no owner)."""
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=None,
        )
        assert link.owner_user_id is None
        assert link.is_owner(None) is True
        assert link.is_owner(self.user_id) is False

    def test_create_link_with_expiration(self):
        """Test creating a link with expiration date."""
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
        """Test creating a link with a project."""
        project_id = uuid4()
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            project_id=project_id,
        )
        assert link.project_id == project_id

    def test_is_owner(self):
        """Test owner verification."""
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        assert link.is_owner(self.user_id) is True
        assert link.is_owner(uuid4()) is False
        assert link.is_owner(None) is False

    def test_is_owner_anonymous_link(self):
        """Test owner verification for anonymous link."""
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=None,
        )
        assert link.is_owner(None) is True
        assert link.is_owner(self.user_id) is False

    def test_is_expired_with_expiration_date(self):
        """Test expiration check with expiration date."""
        expires_at = ExpiresAt.from_datetime(self.future_date)
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            expires_at=expires_at,
        )
        # Not expired before expiration date
        assert not link.is_expired(self.future_date - timedelta(hours=1))
        # Expired after expiration date
        assert link.is_expired(self.future_date + timedelta(hours=1))

    def test_is_expired_without_expiration_date(self):
        """Test expiration check without expiration date."""
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        # Link without expiration is never expired
        assert not link.is_expired(self.future_date)
        assert not link.is_expired(self.past_date)

    def test_is_expired_when_marked_expired(self):
        """Test expiration check when link is marked as expired."""
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
        """Test availability check."""
        expires_at = ExpiresAt.from_datetime(self.future_date)
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
            expires_at=expires_at,
        )
        # Available when not expired and not deleted
        assert link.is_available(self.future_date - timedelta(hours=1)) is True
        # Not available when expired
        assert link.is_available(self.future_date + timedelta(hours=1)) is False

        # Not available when deleted
        link.delete()
        assert link.is_available(self.future_date - timedelta(hours=1)) is False

        # Restore makes it available again
        link.restore()
        assert link.is_available(self.future_date - timedelta(hours=1)) is True

    def test_update_original_url(self):
        """Test updating the original URL."""
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
        """Test updating the short code."""
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
        """Test updating expiration date."""
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

        # Test removing expiration
        link.update_expires_at(None)
        assert link.expires_at is None

    def test_update_project_id(self):
        """Test updating project ID."""
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

        # Test removing project
        link.update_project_id(None)
        assert link.project_id is None

    def test_mark_expired(self):
        """Test marking a link as expired."""
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
        """Test deleting and restoring a link."""
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
        """Test that link properties are immutable through getters."""
        link = Link.create(
            short_code=self.short_code,
            original_url=self.original_url,
            owner_user_id=self.user_id,
        )
        # Should not be able to modify properties directly
        with pytest.raises(AttributeError):
            link.short_code = ShortCode("modified")  # type: ignore
        with pytest.raises(AttributeError):
            link.original_url = OriginalUrl("https://modified.com")  # type: ignore

    def test_link_equality(self):
        """Test that Link instances with same ID are equal."""
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