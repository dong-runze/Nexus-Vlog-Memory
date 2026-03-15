"""
services/video_editor.py
预留调用本地 FFmpeg 拼接视频的函数。
将多段 WaveSpeed 生成的视频片段合并为一个完整的 Vlog。
"""

import subprocess
import tempfile
import os

import httpx


async def download_video(url: str, local_path: str) -> None:
    """下载视频到本地路径"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(response.content)


async def stitch_videos(video_urls: list[str]) -> str:
    """
    将多个视频片段 URL 下载并使用 FFmpeg 拼接成一个完整视频。

    Args:
        video_urls: 视频片段的下载 URL 列表（按播放顺序排列）。

    Returns:
        拼接完成后的本地视频文件路径。

    Raises:
        RuntimeError: FFmpeg 执行失败时。
    """
    # --- TODO: 实现完整逻辑 ---
    # 1. 下载所有视频片段到临时目录
    # 2. 生成 FFmpeg concat 文件列表
    # 3. 调用 FFmpeg 进行拼接
    # 4. 返回输出文件路径

    work_dir = tempfile.mkdtemp(prefix="vlog_")
    output_path = os.path.join(work_dir, "final_vlog.mp4")

    # 步骤 1: 下载视频片段
    local_files: list[str] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, url in enumerate(video_urls):
            if not url:
                continue
            local_path = os.path.join(work_dir, f"clip_{i:03d}.mp4")
            response = await client.get(url)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)
            local_files.append(local_path)

    if not local_files:
        raise RuntimeError("No valid video clips to stitch.")

    # 步骤 2: 生成 FFmpeg concat 列表
    concat_list_path = os.path.join(work_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for file_path in local_files:
            f.write(f"file '{file_path}'\n")

    # 步骤 3: 调用 FFmpeg 拼接
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")

    return output_path
