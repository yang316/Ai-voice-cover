"""Basic API tests for AI Voice Cover backend."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/v1/health."""

    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/api/v1/health").json()
        assert data["status"] == "online"
        assert "gpu" in data
        assert "backends" in data
        assert "features" in data
        assert "gpu_upgradeable" in data
        assert "gpu_detection" in data

    def test_health_gpu_has_structure(self, client):
        data = client.get("/api/v1/health").json()
        gpu = data["gpu"]
        assert "available" in gpu
        assert "device" in gpu


class TestFeaturesEndpoint:
    """Tests for /api/v1/features."""

    def test_features_returns_200(self, client):
        resp = client.get("/api/v1/features")
        assert resp.status_code == 200

    def test_features_has_lists(self, client):
        data = client.get("/api/v1/features").json()
        assert "available" in data
        assert "missing" in data
        assert isinstance(data["available"], list)
        assert isinstance(data["missing"], list)


class TestCoversValidation:
    """Tests for input validation on /api/v1/covers."""

    def test_missing_file_returns_422(self, client):
        resp = client.post("/api/v1/covers", data={"voice_id": "test", "backend": "local"})
        assert resp.status_code == 422  # FastAPI missing required field

    def test_invalid_voice_id_format(self, client):
        resp = client.post("/api/v1/covers", data={
            "voice_id": "../../../etc/passwd",
            "backend": "local",
        }, files={"audio_file": ("test.mp3", b"fake audio data", "audio/mpeg")})
        assert resp.status_code == 400
        assert "Invalid voice_id" in resp.json()["detail"]

    def test_invalid_voice_id_special_chars(self, client):
        resp = client.post("/api/v1/covers", data={
            "voice_id": "test; rm -rf /",
            "backend": "local",
        }, files={"audio_file": ("test.mp3", b"fake audio data", "audio/mpeg")})
        assert resp.status_code == 400

    def test_nonexistent_voice_returns_404(self, client):
        resp = client.post("/api/v1/covers", data={
            "voice_id": "nonexistent_voice_12345",
            "backend": "local",
        }, files={"audio_file": ("test.mp3", b"fake audio data", "audio/mpeg")})
        assert resp.status_code == 404

    def test_invalid_pitch_shift(self, client):
        resp = client.post("/api/v1/covers", data={
            "voice_id": "test_voice",
            "backend": "local",
            "pitch_shift": "100",
        }, files={"audio_file": ("test.mp3", b"fake audio data", "audio/mpeg")})
        # Should be rejected by pitch_shift validation (if voice exists) or 404 (if not)
        assert resp.status_code in (400, 404)


class TestTrainValidation:
    """Tests for input validation on /api/v1/train."""

    @pytest.fixture(autouse=True)
    def _check_train_available(self, client):
        """Skip if training router not loaded (missing ML deps)."""
        features = client.get("/api/v1/features").json()
        if "training" not in features.get("available", []):
            pytest.skip("Training router not loaded (missing ML deps)")

    def test_no_files_returns_422(self, client):
        resp = client.post("/api/v1/train", data={"model_name": "test"})
        assert resp.status_code == 422

    def test_invalid_model_name(self, client):
        resp = client.post("/api/v1/train", data={
            "model_name": "../../../etc/passwd",
        }, files=[("audio_files", ("test.wav", b"\x00" * 2048, "audio/wav"))])
        assert resp.status_code == 400
        assert "model_name" in resp.json()["detail"].lower()

    def test_invalid_model_name_slash(self, client):
        resp = client.post("/api/v1/train", data={
            "model_name": "path/traversal",
        }, files=[("audio_files", ("test.wav", b"\x00" * 2048, "audio/wav"))])
        assert resp.status_code == 400

    def test_invalid_audio_extension(self, client):
        resp = client.post("/api/v1/train", data={
            "model_name": "test_model",
        }, files=[("audio_files", ("test.xyz", b"\x00" * 2048, "application/octet-stream"))])
        assert resp.status_code == 400
        assert "valid audio" in resp.json()["detail"].lower()

    def test_list_training_tasks(self, client):
        resp = client.get("/api/v1/train")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_nonexistent_training_task(self, client):
        resp = client.get("/api/v1/train/nonexistent123")
        assert resp.status_code == 404


class TestTasksList:
    """Tests for /api/v1/tasks."""

    def test_list_tasks_returns_200(self, client):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_nonexistent_task_status(self, client):
        resp = client.get("/api/v1/covers/nonexistent123")
        assert resp.status_code == 404

    def test_nonexistent_download(self, client):
        resp = client.get("/api/v1/covers/nonexistent123/download")
        assert resp.status_code == 404


class TestErrorHandling:
    """Tests for global error handling."""

    def test_404_on_unknown_route(self, client):
        resp = client.get("/api/v1/totally-unknown-endpoint")
        assert resp.status_code in (404, 405)
