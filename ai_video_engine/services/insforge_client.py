"""
services/insforge_client.py
预留与 Insforge BaaS 交互的函数。
用于更新数据库中的视频 URL，以及初始化/读取地图节点数据。
"""

import httpx
from core.config import settings


async def update_node_video(node_id: str, video_url: str) -> dict:
    """
    将生成完成的视频 URL 写入 Insforge 数据库的对应节点记录。

    Args:
        node_id:   前端打卡节点的唯一 ID。
        video_url: WaveSpeed 生成并拼接后的最终视频 URL。

    Returns:
        Insforge API 的响应体（dict）。

    Raises:
        httpx.HTTPStatusError: 请求失败时。
    """
    # --- TODO: 替换为 Insforge 实际 REST API 端点 ---
    api_url = f"{settings.INSFORGE_PROJECT_URL}/rest/v1/landmarks"
    headers = {
        "apikey": settings.INSFORGE_API_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    # 使用 PATCH 更新指定 node_id 的视频字段
    params = {"id": f"eq.{node_id}"}
    payload = {"video_url": video_url}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            api_url, json=payload, headers=headers, params=params
        )
        response.raise_for_status()
        return response.json()


async def get_all_landmarks() -> list[dict]:
    """
    从 Insforge 数据库拉取所有地图节点数据。
    可用于前端初始化时加载云端数据。

    Returns:
        节点数据的列表。
    """
    api_url = f"{settings.INSFORGE_PROJECT_URL}/rest/v1/landmarks"
    headers = {
        "apikey": settings.INSFORGE_API_KEY,
        "Content-Type": "application/json",
    }
    params = {"select": "*", "order": "id.asc"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


async def save_landmark(landmark_data: dict) -> dict:
    """
    向 Insforge 数据库新增或更新一个地图节点。

    Args:
        landmark_data: 节点数据字典，需包含 id, name, lat, lng 等字段。

    Returns:
        Insforge API 的响应体。
    """
    api_url = f"{settings.INSFORGE_PROJECT_URL}/rest/v1/landmarks"
    headers = {
        "apikey": settings.INSFORGE_API_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(api_url, json=landmark_data, headers=headers)
        response.raise_for_status()
        return response.json()
