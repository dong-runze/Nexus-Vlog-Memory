"""
services/gcs_client.py
Google Cloud Storage 客户端 - 支持上传视频并生成短期签名链接（Signed URL）。
"""

import asyncio
import datetime
import os

from google.cloud import storage


def _get_client_and_bucket():
    """初始化并返回 GCS 客户端和 Bucket 对象。"""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME 环境变量未设置")

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        return storage_client, bucket, bucket_name
    except Exception as e:
        print(f"[GCS] 初始化客户端失败: {e}")
        raise e


async def upload_video(local_file_path: str, destination_blob_name: str) -> str:
    """
    将本地视频文件上传到 Google Cloud Storage。

    Returns:
        destination_blob_name (str): GCS Blob 路径名（不是 URL）。
        调用方应通过 generate_signed_url(blob_name) 获取临时访问链接。
    """
    _, bucket, bucket_name = _get_client_and_bucket()

    blob = bucket.blob(destination_blob_name)
    blob.content_type = 'video/mp4'

    print(f"[GCS] 正在上传 {local_file_path} 到 {bucket_name}/{destination_blob_name} ...")

    try:
        await asyncio.to_thread(blob.upload_from_filename, local_file_path)
    except Exception as e:
        print(f"[GCS] 上传文件失败: {e}")
        raise e

    print(f"[GCS] 上传成功！Blob Name: {destination_blob_name}")
    # 返回 blob 名称，而不是固定 URL
    return destination_blob_name


def download_blob(blob_name: str, destination_path: str) -> None:
    """
    使用 GCS SDK 将云端 Blob 直接下载到本地路径，完全绕过 Signed URL。

    Args:
        blob_name: GCS 对象路径（如 \"USS/master/clips/clip_xxxx.mp4\"）。
        destination_path: 本地目标文件路径。
    """
    _, bucket, bucket_name = _get_client_and_bucket()
    blob = bucket.blob(blob_name)
    print(f"[GCS] 下载 {bucket_name}/{blob_name} → {destination_path} ...")
    blob.download_to_filename(destination_path)
    print(f"[GCS] 下载完成: {destination_path}")


def generate_signed_url(blob_name: str, expiration_minutes: int = 60) -> str:
    """
    为 GCS 中的私有对象生成一个限时可访问的签名链接（Signed URL v4）。

    Args:
        blob_name: GCS 对象路径（如 "clips/landmark_1234.mp4"）。
        expiration_minutes: 链接有效期（分钟），默认 60 分钟。

    Returns:
        签名访问链接（str），过期后失效。
    """
    _, bucket, _ = _get_client_and_bucket()

    blob = bucket.blob(blob_name)

    try:
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="GET",
        )
        print(f"[GCS] Signed URL generated for {blob_name}: {signed_url[:80]}...")
        return signed_url
    except Exception as e:
        print(f"[GCS] 生成签名链接失败: {e}")
        raise e


async def upload_image_bytes(
    file_bytes: bytes,
    destination_blob_name: str,
    content_type: str = "image/jpeg",
) -> str:
    """
    将图片字节流直接上传到 GCS，设置公开可读，返回公开访问 URL。

    Args:
        file_bytes: 图片原始字节。
        destination_blob_name: GCS 对象路径，如 "images/USS/master/img_xxxx.jpg"。
        content_type: MIME 类型，默认 image/jpeg。

    Returns:
        公开访问 URL (str)。
    """
    _, bucket, bucket_name = _get_client_and_bucket()
    blob = bucket.blob(destination_blob_name)
    blob.content_type = content_type

    print(f"[GCS] 上传图片到 {bucket_name}/{destination_blob_name} ({len(file_bytes)} bytes)...")

    try:
        await asyncio.to_thread(
            blob.upload_from_string, file_bytes, content_type=content_type
        )
    except Exception as e:
        print(f"[GCS] 图片上传失败: {e}")
        raise e

    # Uniform bucket-level access 已启用，不能用 make_public()
    # 改为生成 7 天有效的 Signed URL（与视频 URL 策略一致）
    try:
        import datetime
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(days=7),
            method="GET",
        )
        print(f"[GCS] 图片 Signed URL 生成成功: {signed_url[:80]}...")
        return signed_url
    except Exception as e:
        print(f"[GCS] Signed URL 生成失败: {e}")
        raise e
