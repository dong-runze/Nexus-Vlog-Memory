"""
schemas/response.py
统一响应格式定义
"""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel


class ResponseCode:
    """响应码"""
    SUCCESS = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMITED = 429
    INTERNAL_ERROR = 500


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = ResponseCode.SUCCESS
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=ResponseCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str) -> "ApiResponse[None]":
        return cls(code=code, message=message, data=None)


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    task_type: str
    status: str
    progress: int
    total: int
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    estimated_time_remaining: Optional[int] = None
    metadata: dict[str, Any] = {}


class VideoClipTaskStatusResponse(TaskStatusResponse):
    """视频片段任务状态响应"""
    pass


class VideoStitchTaskStatusResponse(TaskStatusResponse):
    """视频拼接任务状态响应 - 包含视频参数"""
    resolution: Optional[str] = None
    bitrate: Optional[str] = None
    duration: Optional[float] = None
    clip_count: Optional[int] = None
