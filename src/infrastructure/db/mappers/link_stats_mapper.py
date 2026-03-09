from ....domain.entities.link_stats import LinkStats
from ..models.link_stats import LinkStatsModel


def link_stats_to_model(stats: LinkStats) -> LinkStatsModel:
    return LinkStatsModel(
        link_id=stats.link_id,
        clicks=stats.clicks,
        last_used_at=stats.last_used_at,
        created_at=stats.created_at,
    )


def model_to_link_stats(model: LinkStatsModel) -> LinkStats:
    return LinkStats(
        link_id=model.link_id,
        clicks=model.clicks,
        last_used_at=model.last_used_at,
        created_at=model.created_at,
    )