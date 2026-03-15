"""
models/task.py
任务模型定义
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class TaskType(str, Enum):
    """任务类型"""
    VIDEO_CLIP = "video_clip"      # 视频片段生成
    VIDEO_STITCH = "video_stitch"  # 视频拼接


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"   # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


class Task:
    """任务模型"""

    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        status: TaskStatus = TaskStatus.PENDING,
        progress: int = 0,
        total: int = 100,
        result: Optional[str] = None,
        error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        estimated_time_remaining: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.task_id = task_id or str(uuid.uuid4())
        self.task_type = task_type
        self.status = status
        self.progress = progress
        self.total = total
        self.result = result
        self.error = error
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.estimated_time_remaining = estimated_time_remaining
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "estimated_time_remaining": self.estimated_time_remaining,
            "metadata": self.metadata,
        }


class VideoClipTaskMetadata:
    """视频片段任务元数据"""

    def __init__(
        self,
        prompt: str,
        node_name: str = "attraction",
        resolution: str = "720p",
        duration: int = 3,
    ):
        self.prompt = prompt
        self.node_name = node_name
        self.resolution = resolution
        self.duration = duration


class VideoStitchTaskMetadata:
    """视频拼接任务元数据"""

    def __init__(
        self,
        video_urls: list[str],
        output_resolution: str = "1920x1080",
        output_bitrate: str = "5M",
    ):
        self.video_urls = video_urls
        self.output_resolution = output_resolution
        self.output_bitrate = output_bitrate


class VideoStitchResult:
    """视频拼接结果"""

    def __init__(
        self,
        output_path: str,
        resolution: str,
        bitrate: str,
        duration: float,
        clip_count: int,
    ):
        self.output_path = output_path
        self.resolution = resolution
        self.bitrate = bitrate
        self.duration = duration
        self.clip_count = clip_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "resolution": self.resolution,
            "bitrate": self.bitrate,
            "duration": self.duration,
            "clip_count": self.clip_count,
        }
