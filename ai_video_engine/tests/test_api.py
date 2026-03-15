"""
tests/test_api.py
单元测试
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from models.task import Task, TaskStatus, TaskType
from services.task_store import task_store, RateLimiter


client = TestClient(app)


API_KEY = "dev-api-key-12345"
HEADERS = {"X-API-Key": API_KEY}


class TestHealthEndpoint:
    """健康检查接口测试"""

    def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert "status" in data["data"]


class TestAuthMiddleware:
    """身份验证中间件测试"""

    def test_without_api_key(self):
        """测试无 API Key 访问"""
        response = client.post(
            "/api/v1/generate-clip",
            json={"prompt": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 401

    def test_with_invalid_api_key(self):
        """测试无效 API Key"""
        response = client.post(
            "/api/v1/generate-clip",
            json={"prompt": "test"},
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 401

    def test_with_valid_api_key(self):
        """测试有效 API Key"""
        response = client.post(
            "/api/v1/generate-clip",
            json={"prompt": "test prompt"},
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestRateLimiter:
    """限流器测试"""

    def test_rate_limiter_allows_requests(self):
        """测试限流器允许请求"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        client_id = "test-client"

        for _ in range(5):
            assert limiter.is_allowed(client_id) is True

    def test_rate_limiter_blocks_excess_requests(self):
        """测试限流器阻止超额请求"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        client_id = "test-client-2"

        for _ in range(3):
            limiter.is_allowed(client_id)

        assert limiter.is_allowed(client_id) is False

    def test_rate_limiter_remaining(self):
        """测试剩余请求次数"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        client_id = "test-client-3"

        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        assert limiter.get_remaining(client_id) == 8


class TestTaskStore:
    """任务存储测试"""

    def test_create_and_get_task(self):
        """测试创建和获取任务"""
        task_store._tasks.clear()

        task = Task(
            task_id="test-001",
            task_type=TaskType.VIDEO_CLIP,
            metadata={"prompt": "test"}
        )
        created = task_store.create_task(task)

        assert created.task_id == "test-001"
        retrieved = task_store.get_task("test-001")
        assert retrieved is not None
        assert retrieved.task_id == "test-001"

    def test_update_task(self):
        """测试更新任务"""
        task_store._tasks.clear()

        task = Task(
            task_id="test-002",
            task_type=TaskType.VIDEO_STITCH,
            metadata={"video_urls": []}
        )
        task_store.create_task(task)

        task.status = TaskStatus.PROCESSING
        task.progress = 50
        updated = task_store.update_task(task)

        assert updated.status == TaskStatus.PROCESSING
        assert updated.progress == 50

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        task_store._tasks.clear()
        result = task_store.get_task("non-existent")
        assert result is None


class TestVideoClipEndpoint:
    """视频片段生成接口测试"""

    def test_generate_clip_success(self):
        """测试视频片段生成成功"""
        task_store._tasks.clear()

        response = client.post(
            "/api/v1/generate-clip",
            json={"prompt": "A fun roller coaster ride"},
            headers=HEADERS
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]

    def test_generate_clip_empty_prompt(self):
        """测试空 prompt"""
        response = client.post(
            "/api/v1/generate-clip",
            json={"prompt": ""},
            headers=HEADERS
        )

        assert response.status_code == 400 or response.status_code == 422


class TestVideoStitchEndpoint:
    """视频拼接接口测试"""

    def test_stitch_vlog_success(self):
        """测试视频拼接成功"""
        task_store._tasks.clear()

        response = client.post(
            "/api/v1/stitch-vlog",
            json={
                "video_urls": [
                    "https://example.com/video1.mp4",
                    "https://example.com/video2.mp4"
                ]
            },
            headers=HEADERS
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]
        assert "2 个片段" in data["data"]["message"]

    def test_stitch_vlog_empty_urls(self):
        """测试空 URL 列表"""
        response = client.post(
            "/api/v1/stitch-vlog",
            json={"video_urls": []},
            headers=HEADERS
        )

        assert response.status_code == 400


class TestTaskStatusEndpoint:
    """任务状态查询接口测试"""

    def test_get_task_status_success(self):
        """测试获取任务状态成功"""
        task_store._tasks.clear()

        create_response = client.post(
            "/api/v1/stitch-vlog",
            json={"video_urls": ["https://example.com/video.mp4"]},
            headers=HEADERS
        )
        task_id = create_response.json()["data"]["task_id"]

        status_response = client.get(
            f"/task/{task_id}/status",
            headers=HEADERS
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["code"] == 0
        assert data["data"]["task_id"] == task_id
        assert data["data"]["task_type"] == "video_stitch"
        assert data["data"]["status"] in ["pending", "processing", "completed", "failed"]

    def test_get_task_status_not_found(self):
        """测试获取不存在的任务"""
        response = client.get(
            "/task/non-existent-task/status",
            headers=HEADERS
        )

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
