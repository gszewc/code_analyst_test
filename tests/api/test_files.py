"""File endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import io

from codeminer.components.file_manager import FileInfo
from tests.api.conftest import create_mock_upload_session


class TestUploadZip:
    """Test ZIP upload endpoint."""
    
    def test_upload_zip_success(self, test_client: TestClient, sample_project_id: str, api_mocks, sample_upload_session):
        """Test successful ZIP upload."""
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            return sample_upload_session
        
        api_mocks['file_service'].upload_zip = mock_upload_zip
        
        file_content = b"PK test zip content"
        file = io.BytesIO(file_content)
        
        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test.zip", file, "application/zip")}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["file_count"] == 5
    
    def test_upload_zip_invalid_file_type(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test uploading non-ZIP file."""
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        api_mocks['file_service'].upload_zip = mock_upload_zip
        
        file_content = b"not a zip file"
        file = io.BytesIO(file_content)
        
        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test.txt", file, "text/plain")}
        )
        
        assert response.status_code == 400
    
    def test_upload_zip_empty_file(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test uploading empty file."""
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Empty file")
        
        api_mocks['file_service'].upload_zip = mock_upload_zip
        
        file_content = b""
        file = io.BytesIO(file_content)
        
        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("empty.zip", file, "application/zip")}
        )
        
        assert response.status_code == 400
    
    def test_upload_zip_project_not_found(self, test_client: TestClient, api_mocks):
        """Test uploading to non-existent project."""
        project_id = str(uuid4())
        
        def mock_upload_zip(pid, file, max_size=20*1024*1024):
            raise Exception("Project not found")
        
        api_mocks['file_service'].upload_zip = mock_upload_zip
        
        file_content = b"PK test"
        file = io.BytesIO(file_content)
        
        response = test_client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("test.zip", file, "application/zip")}
        )
        
        assert response.status_code == 500

    def test_upload_zip_async_service(self, test_client: TestClient, sample_project_id: str, api_mocks, sample_upload_session):
        """Test upload supports awaitable service results."""
        async def mock_upload_zip(pid, file, max_size=20*1024*1024):
            return sample_upload_session

        api_mocks['file_service'].upload_zip = mock_upload_zip

        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/upload",
            files={"file": ("test.zip", io.BytesIO(b"PK async"), "application/zip")}
        )

        assert response.status_code == 201


class TestListFiles:
    """Test file listing endpoint."""
    
    def test_list_files(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test listing files in project."""
        mock_file_info = FileInfo("test.py", "test.py", 1024, is_directory=False)
        
        def mock_list_files(pid, path=""):
            return [mock_file_info]
        
        api_mocks['file_service'].list_files = mock_list_files
        
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files")
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "total" in data

    def test_list_files_invalid_path(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test listing files with invalid path."""
        def mock_list_files(pid, path=""):
            raise ValueError("Invalid path")

        api_mocks['file_service'].list_files = mock_list_files

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files?path=../bad")

        assert response.status_code == 400


class TestGetFileContent:
    """Test file content endpoint."""
    
    def test_get_file_content(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test getting file content."""
        def mock_get_content(pid, file_path):
            return "print('hello')"
        
        api_mocks['file_service'].get_file_content = mock_get_content
        
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files/test.py")
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
    
    def test_get_file_content_not_found(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test getting non-existent file."""
        def mock_get_content(pid, file_path):
            raise FileNotFoundError("File not found")
        
        api_mocks['file_service'].get_file_content = mock_get_content
        
        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files/nonexistent.py")
        
        assert response.status_code == 404

    def test_get_file_content_invalid_path(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test getting file content with invalid path."""
        def mock_get_content(pid, file_path):
            raise ValueError("Invalid file path")

        api_mocks['file_service'].get_file_content = mock_get_content

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files/test.py")

        assert response.status_code == 400

    def test_get_file_content_nested_relative_path(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test getting content using nested project-relative source file path."""
        def mock_get_content(pid, file_path):
            assert file_path == "application/app.py"
            return "print('ok')"

        api_mocks['file_service'].get_file_content = mock_get_content

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/files/application/app.py"
        )

        assert response.status_code == 200
        assert response.json()["content"] == "print('ok')"


class TestCreateFolder:
    """Test folder creation endpoint."""
    
    def test_create_folder(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test creating folder."""
        folder_path = "new_folder"
        
        def mock_create_folder(pid, path):
            pass
        
        api_mocks['file_service'].create_folder = mock_create_folder
        
        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/folders?folder_path={folder_path}"
        )
        
        assert response.status_code == 201

    def test_create_folder_invalid_path(self, test_client: TestClient, sample_project_id: str, api_mocks):
        """Test creating folder with invalid path."""
        def mock_create_folder(pid, path):
            raise ValueError("Invalid folder path")

        api_mocks['file_service'].create_folder = mock_create_folder

        response = test_client.post(
            f"/api/v1/projects/{sample_project_id}/folders?folder_path=../outside"
        )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Symlink browsing API tests (US1)
# ---------------------------------------------------------------------------


class TestSymlinkFileBrowsing:
    """API tests for file browsing through symlinked directories and files."""

    def test_list_files_includes_symlinked_directory(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Listing a directory should include symlinked subdirectory entries."""
        from codeminer.components.file_manager import FileInfo

        linked_dir = FileInfo("lib", "lib", 0, is_directory=True)
        regular_file = FileInfo("main.py", "main.py", 100)

        def mock_list_files(pid, path=""):
            return [regular_file, linked_dir]

        api_mocks["file_service"].list_files = mock_list_files

        response = test_client.get(f"/api/v1/projects/{sample_project_id}/files")

        assert response.status_code == 200
        data = response.json()
        names = [f["name"] for f in data["files"]]
        assert "lib" in names
        assert "main.py" in names
        # lib is listed as a directory
        lib_entry = next(f for f in data["files"] if f["name"] == "lib")
        assert lib_entry["is_directory"] is True

    def test_list_files_inside_symlinked_directory(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Listing inside a symlinked directory returns its contents."""
        from codeminer.components.file_manager import FileInfo

        def mock_list_files(pid, path=""):
            if path == "lib":
                return [FileInfo("lib/utils.py", "utils.py", 50)]
            return []

        api_mocks["file_service"].list_files = mock_list_files

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/files?path=lib"
        )

        assert response.status_code == 200
        data = response.json()
        names = [f["name"] for f in data["files"]]
        assert "utils.py" in names

    def test_read_file_through_alias_path(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Reading a file via an alias path should return its content."""
        def mock_get_file_content(pid, path):
            if path == "lib/utils.py":
                return "def helper(): pass\n"
            raise Exception("Not found")

        api_mocks["file_service"].get_file_content = mock_get_file_content

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/files/lib/utils.py"
        )

        assert response.status_code == 200
        assert response.json()["content"] == "def helper(): pass\n"

    def test_read_broken_symlink_returns_controlled_error(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """Reading a file through a broken symlink should return 404."""
        from fastapi import HTTPException

        def mock_get_file_content(pid, path):
            raise HTTPException(status_code=404, detail="File not found: broken/file.py")

        api_mocks["file_service"].get_file_content = mock_get_file_content

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/files/broken/file.py"
        )

        assert response.status_code == 404

    def test_traversal_path_rejected(
        self, test_client: TestClient, sample_project_id: str, api_mocks
    ):
        """A path containing '..' must be rejected with a 400 error."""
        from fastapi import HTTPException

        def mock_get_file_content(pid, path):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path. Use normalized relative paths",
            )

        api_mocks["file_service"].get_file_content = mock_get_file_content

        response = test_client.get(
            f"/api/v1/projects/{sample_project_id}/files/../../../etc/passwd"
        )

        assert response.status_code in (400, 404)
