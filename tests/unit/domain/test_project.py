import pytest
from uuid import UUID, uuid4

from src.domain.entities.project import Project


class TestProject:
    def setup_method(self):
        
        self.owner_id = uuid4()
        self.project_name = "Test Project"

    def test_create_project(self):
        
        project = Project.create(self.project_name, self.owner_id)
        assert project.name == self.project_name
        assert project.owner_user_id == self.owner_id
        assert isinstance(project.id, UUID)
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_create_project_trims_name(self):
        
        project = Project.create("  Test Project  ", self.owner_id)
        assert project.name == "Test Project"

    def test_create_project_empty_name(self):
        
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project.create("", self.owner_id)
        with pytest.raises(ValueError):
            Project.create("   ", self.owner_id)

    def test_create_project_name_too_long(self):
        
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Project name cannot exceed 100 characters"):
            Project.create(long_name, self.owner_id)

    def test_create_project_name_max_length(self):
        
        long_name = "a" * 100
        project = Project.create(long_name, self.owner_id)
        assert project.name == long_name
        assert len(project.name) == 100

    def test_update_name(self):
        
        project = Project.create(self.project_name, self.owner_id)
        new_name = "Updated Project Name"
        original_updated_at = project.updated_at

        project.update_name(new_name)
        assert project.name == new_name
        assert project.updated_at > original_updated_at

    def test_update_name_trims_whitespace(self):
        
        project = Project.create(self.project_name, self.owner_id)
        project.update_name("  New Name  ")
        assert project.name == "New Name"

    def test_update_name_empty(self):
        
        project = Project.create(self.project_name, self.owner_id)
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            project.update_name("")
        with pytest.raises(ValueError):
            project.update_name("   ")

    def test_update_name_too_long(self):
        
        project = Project.create(self.project_name, self.owner_id)
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Project name cannot exceed 100 characters"):
            project.update_name(long_name)

    def test_is_owner(self):
        
        project = Project.create(self.project_name, self.owner_id)
        assert project.is_owner(self.owner_id) is True
        assert project.is_owner(uuid4()) is False
        assert project.is_owner(None) is False

    def test_project_immutable_properties(self):
        
        project = Project.create(self.project_name, self.owner_id)
        
        with pytest.raises(AttributeError):
            project.name = "Modified Name"  
        with pytest.raises(AttributeError):
            project.owner_user_id = uuid4()  

    def test_project_equality(self):
        
        project1 = Project.create("Project 1", self.owner_id)
        project2 = Project.create("Project 2", uuid4())
        assert project1 != project2
        assert project1 == project1

    def test_direct_instantiation(self):
        
        project = Project(self.project_name, self.owner_id)
        assert project.name == self.project_name
        assert project.owner_user_id == self.owner_id

    def test_direct_instantiation_with_id(self):
        
        project_id = uuid4()
        project = Project(self.project_name, self.owner_id, id=project_id)
        assert project.id == project_id