"""
Tests for ProjectStorage - SQLite project CRUD operations.
"""

import pytest
from datetime import datetime

from codeminer.database.project_storage import (
    ProjectStorage,
    ProjectValidationError,
    ProjectNotFoundError,
    ProjectConflictError
)


class TestProjectStorage:
    """Tests for ProjectStorage."""

    @pytest.fixture
    def storage(self, sqlite_manager):
        """Create ProjectStorage instance."""
        return ProjectStorage(sqlite_manager)

    def test_create_project(self, storage):
        """Test creating a project."""
        project = storage.create_project('test-project', 'Test description')
        
        assert project.id is not None
        assert project.name == 'test-project'
        assert project.description == 'Test description'
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

    def test_create_project_minimal(self, storage):
        """Test creating a project with minimal data."""
        project = storage.create_project('minimal-project')
        
        assert project.name == 'minimal-project'
        assert project.description == ''

    def test_create_project_duplicate_name(self, storage):
        """Test creating project with duplicate name raises error."""
        storage.create_project('test-project', 'First')
        
        with pytest.raises(ProjectConflictError, match='already exists'):
            storage.create_project('test-project', 'Second')

    def test_create_project_invalid_name_empty(self, storage):
        """Test creating project with empty name raises error."""
        with pytest.raises(ProjectValidationError, match='required'):
            storage.create_project('')

    def test_create_project_invalid_name_whitespace(self, storage):
        """Test creating project with whitespace-only name raises error."""
        with pytest.raises(ProjectValidationError, match='required'):
            storage.create_project('   ')

    def test_create_project_invalid_name_special_chars(self, storage):
        """Test creating project with invalid characters raises error."""
        with pytest.raises(ProjectValidationError, match='alphanumeric'):
            storage.create_project('test@project!')

    def test_create_project_invalid_name_too_long(self, storage):
        """Test creating project with name too long raises error."""
        long_name = 'a' * 300
        with pytest.raises(ProjectValidationError, match='<= 255'):
            storage.create_project(long_name)

    def test_create_project_valid_names(self, storage):
        """Test creating projects with valid names."""
        valid_names = [
            'simple',
            'with-dash',
            'with_underscore',
            'With123Numbers',
            'a',  # Single character
            'a' * 255,  # Max length
        ]
        
        for name in valid_names:
            project = storage.create_project(name)
            assert project.name == name

    def test_get_project(self, storage):
        """Test getting a project by ID."""
        created = storage.create_project('test-project', 'Description')
        
        retrieved = storage.get_project(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.description == created.description

    def test_get_project_not_found(self, storage):
        """Test getting non-existent project returns None."""
        result = storage.get_project('nonexistent-id')
        assert result is None

    def test_get_project_or_raise(self, storage):
        """Test getting project or raising exception."""
        created = storage.create_project('test-project')
        
        retrieved = storage.get_project_or_raise(created.id)
        assert retrieved.id == created.id

    def test_get_project_or_raise_not_found(self, storage):
        """Test getting non-existent project raises exception."""
        with pytest.raises(ProjectNotFoundError, match='not found'):
            storage.get_project_or_raise('nonexistent-id')

    def test_list_projects(self, storage):
        """Test listing projects."""
        # Create multiple projects
        projects = []
        for i in range(5):
            project = storage.create_project(f'project-{i}', f'Description {i}')
            projects.append(project)
        
        # List all
        listed = storage.list_projects()
        
        assert len(listed) == 5
        # Should be ordered by created_at descending
        assert listed[0].name == 'project-4'

    def test_list_projects_limit(self, storage):
        """Test listing projects with limit."""
        # Create 10 projects
        for i in range(10):
            storage.create_project(f'project-{i}')
        
        # List with limit
        listed = storage.list_projects(limit=3)
        assert len(listed) == 3

    def test_update_project_name(self, storage):
        """Test updating project name."""
        project = storage.create_project('old-name', 'Description')

        # Small delay to ensure timestamp difference
        import time
        time.sleep(1.01)  # SQLite CURRENT_TIMESTAMP has 1 second precision

        updated = storage.update_project(project.id, name='new-name')

        assert updated.name == 'new-name'
        assert updated.description == 'Description'
        # updated_at should be >= created_at
        assert updated.updated_at >= updated.created_at

    def test_update_project_description(self, storage):
        """Test updating project description."""
        project = storage.create_project('test', 'Old description')
        
        updated = storage.update_project(project.id, description='New description')
        
        assert updated.name == 'test'
        assert updated.description == 'New description'

    def test_update_project_not_found(self, storage):
        """Test updating non-existent project raises error."""
        with pytest.raises(ProjectNotFoundError):
            storage.update_project('nonexistent-id', name='new-name')

    def test_update_project_duplicate_name(self, storage):
        """Test updating to duplicate name raises error."""
        storage.create_project('project-1')
        project2 = storage.create_project('project-2')
        
        with pytest.raises(ProjectConflictError, match='already exists'):
            storage.update_project(project2.id, name='project-1')

    def test_delete_project(self, storage):
        """Test deleting a project."""
        project = storage.create_project('test-project')
        
        # Delete
        storage.delete_project(project.id)
        
        # Should not exist
        retrieved = storage.get_project(project.id)
        assert retrieved is None

    def test_delete_project_not_found(self, storage):
        """Test deleting non-existent project raises error."""
        with pytest.raises(ProjectNotFoundError):
            storage.delete_project('nonexistent-id')

    def test_delete_project_cascade(self, storage, sqlite_manager):
        """Test deleting project cascades to analyses."""
        # Create project
        project = storage.create_project('test-project')
        
        # Create analysis
        conn = sqlite_manager.get_connection()
        conn.execute(
            'INSERT INTO analyses (id, project_id) VALUES (?, ?)',
            ('analysis-id', project.id)
        )
        conn.commit()
        
        # Delete project
        storage.delete_project(project.id)
        
        # Analysis should be deleted too
        cursor = conn.execute(
            'SELECT COUNT(*) FROM analyses WHERE id = ?',
            ('analysis-id',)
        )
        count = cursor.fetchone()[0]
        assert count == 0

    def test_project_validation_name_pattern(self, storage):
        """Test project name validation pattern."""
        # Valid names
        for name in ['test', 'test-123', 'test_abc', 'A1B2C3']:
            project = storage.create_project(name)
            assert project.name == name
        
        # Invalid names
        for name in ['test.project', 'test project', 'test@project']:
            with pytest.raises(ProjectValidationError):
                storage.create_project(name)

    def test_project_validation_description_length(self, storage):
        """Test description length validation."""
        # Valid description
        storage.create_project('test', 'a' * 1000)
        
        # Invalid - too long
        with pytest.raises(ProjectValidationError, match='<= 1000'):
            storage.create_project('test-2', 'a' * 1001)


class TestProjectStorageIntegration:
    """Integration tests with real SQLite."""

    def test_full_crud_lifecycle(self, sqlite_manager):
        """Test complete CRUD lifecycle."""
        storage = ProjectStorage(sqlite_manager)
        
        # Create
        project = storage.create_project('lifecycle-test', 'Testing CRUD')
        assert project.id is not None
        
        # Read
        retrieved = storage.get_project_or_raise(project.id)
        assert retrieved.name == 'lifecycle-test'
        
        # Update
        updated = storage.update_project(
            project.id,
            name='updated-test',
            description='Updated description'
        )
        assert updated.name == 'updated-test'
        
        # Delete
        storage.delete_project(project.id)
        assert storage.get_project(project.id) is None

    def test_multiple_projects(self, sqlite_manager):
        """Test managing multiple projects."""
        storage = ProjectStorage(sqlite_manager)
        
        # Create multiple
        projects = [
            storage.create_project(f'project-{i}', f'Desc {i}')
            for i in range(3)
        ]
        
        # List
        all_projects = storage.list_projects()
        assert len(all_projects) == 3
        
        # Get each
        for project in projects:
            retrieved = storage.get_project(project.id)
            assert retrieved is not None
