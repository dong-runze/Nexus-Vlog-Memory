"""
services/task_store.py
任务存储层 - 内存存储 + 限流机制
"""
import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from models.task import Task, TaskStatus, TaskType


class RateLimiter:
    """简单限流器 - 基于令牌桶算法"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds

            # 清理过期请求记录
            self.requests[client_id] = [
                t for t in self.requests[client_id] if t > window_start
            ]

            if len(self.requests[client_id]) >= self.max_requests:
                return False

            self.requests[client_id].append(now)
            return True

    def get_remaining(self, client_id: str) -> int:
        """获取剩余请求次数"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds
            self.requests[client_id] = [
                t for t in self.requests[client_id] if t > window_start
            ]
            return max(0, self.max_requests - len(self.requests[client_id]))


class TaskStore:
    """任务存储层 - 内存存储"""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()

    def create_task(self, task: Task) -> Task:
        """创建任务"""
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task: Task) -> Task:
        """更新任务"""
        with self._lock:
            task.updated_at = datetime.now()
            self._tasks[task.task_id] = task
        return task

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """获取指定类型的所有任务"""
        with self._lock:
            return [
                task for task in self._tasks.values()
                if task.task_type == task_type
            ]

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """获取指定状态的所有任务"""
        with self._lock:
            return [
                task for task in self._tasks.values()
                if task.status == status
            ]

    def cleanup_old_tasks(self, hours: int = 24) -> int:
        """清理旧任务"""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            task_ids = [
                task_id for task_id, task in self._tasks.items()
                if task.updated_at < cutoff
            ]
            for task_id in task_ids:
                del self._tasks[task_id]
            return len(task_ids)


# 全局单例
task_store = TaskStore()

# 全局限流器 - 每分钟100次请求
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
