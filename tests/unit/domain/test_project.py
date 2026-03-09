import pytest
from uuid import UUID, uuid4

from src.domain.entities.project import Project


class TestProject:
    def setup_method(self):
        """Setup common test data."""
        self.owner_id = uuid4()
        self.project_name = "Test Project"

    def test_create_project(self):
        """Test creating a project with valid name and owner."""
        project = Project.create(self.project_name, self.owner_id)
        assert project.name == self.project_name
        assert project.owner_user_id == self.owner_id
        assert isinstance(project.id, UUID)
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_create_project_trims_name(self):
        """Test that project name is trimmed of whitespace."""
        project = Project.create("  Test Project  ", self.owner_id)
        assert project.name == "Test Project"

    def test_create_project_empty_name(self):
        """Test that empty project name raises error."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project.create("", self.owner_id)
        with pytest.raises(ValueError):
            Project.create("   ", self.owner_id)

    def test_create_project_name_too_long(self):
        """Test that project name exceeding 100 characters raises error."""
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Project name cannot exceed 100 characters"):
            Project.create(long_name, self.owner_id)

    def test_create_project_name_max_length(self):
        """Test project name at maximum allowed length (100 characters)."""
        long_name = "a" * 100
        project = Project.create(long_name, self.owner_id)
        assert project.name == long_name
        assert len(project.name) == 100

    def test_update_name(self):
        """Test updating project name."""
        project = Project.create(self.project_name, self.owner_id)
        new_name = "Updated Project Name"
        original_updated_at = project.updated_at

        project.update_name(new_name)
        assert project.name == new_name
        assert project.updated_at > original_updated_at

    def test_update_name_trims_whitespace(self):
        """Test that update_name trims whitespace."""
        project = Project.create(self.project_name, self.owner_id)
        project.update_name("  New Name  ")
        assert project.name == "New Name"

    def test_update_name_empty(self):
        """Test that updating to empty name raises error."""
        project = Project.create(self.project_name, self.owner_id)
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            project.update_name("")
        with pytest.raises(ValueError):
            project.update_name("   ")

    def test_update_name_too_long(self):
        """Test that updating to name exceeding 100 characters raises error."""
        project = Project.create(self.project_name, self.owner_id)
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Project name cannot exceed 100 characters"):
            project.update_name(long_name)

    def test_is_owner(self):
        """Test owner verification."""
        project = Project.create(self.project_name, self.owner_id)
        assert project.is_owner(self.owner_id) is True
        assert project.is_owner(uuid4()) is False
        assert project.is_owner(None) is False

    def test_project_immutable_properties(self):
        """Test that project properties are immutable through getters."""
        project = Project.create(self.project_name, self.owner_id)
        # Should not be able to modify properties directly
        with pytest.raises(AttributeError):
            project.name = "Modified Name"  # type: ignore
        with pytest.raises(AttributeError):
            project.owner_user_id = uuid4()  # type: ignore

    def test_project_equality(self):
        """Test that Project instances with same ID are equal."""
        project1 = Project.create("Project 1", self.owner_id)
        project2 = Project.create("Project 2", uuid4())
        assert project1 != project2
        assert project1 == project1

    def test_direct_instantiation(self):
        """Test creating project directly (not using create method)."""
        project = Project(self.project_name, self.owner_id)
        assert project.name == self.project_name
        assert project.owner_user_id == self.owner_id

    def test_direct_instantiation_with_id(self):
        """Test creating project with existing ID."""
        project_id = uuid4()
        project = Project(self.project_name, self.owner_id, id=project_id)
        assert project.id == project_id