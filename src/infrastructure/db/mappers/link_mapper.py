from ....domain.entities.link import Link
from ....domain.value_objects.expires_at import ExpiresAt
from ....domain.value_objects.original_url import OriginalUrl
from ....domain.value_objects.short_code import ShortCode
from ..models.link import LinkModel
from datetime import timezone


def link_to_model(link: Link) -> LinkModel:
    return LinkModel(
        id=link.id,
        short_code=str(link.short_code),
        original_url=str(link.original_url),
        owner_user_id=link.owner_user_id,
        project_id=link.project_id,
        expires_at=link.expires_at.value if link.expires_at else None,
        expired_at=link.expired_at,
        is_deleted=link.is_deleted,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def model_to_link(model: LinkModel) -> Link:
    return Link(
        id=model.id,
        short_code=ShortCode.from_string(model.short_code),
        original_url=OriginalUrl.from_string(model.original_url),
        owner_user_id=model.owner_user_id,
        expires_at=ExpiresAt.from_datetime(
            model.expires_at.replace(tzinfo=timezone.utc) if model.expires_at.tzinfo is None else model.expires_at
        ) if model.expires_at else None,
        project_id=model.project_id,
        expired_at=model.expired_at,
        is_deleted=model.is_deleted,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )