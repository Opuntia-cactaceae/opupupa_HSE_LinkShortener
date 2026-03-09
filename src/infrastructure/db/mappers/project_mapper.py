from ....domain.entities.project import Project
from ..models.project import ProjectModel


def project_to_model(project: Project) -> ProjectModel:
    return ProjectModel(
        id=project.id,
        name=project.name,
        owner_user_id=project.owner_user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def model_to_project(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        name=model.name,
        owner_user_id=model.owner_user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )