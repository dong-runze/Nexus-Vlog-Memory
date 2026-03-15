"""
services/video_stitcher.py
影院级 Vlog 拼接引擎 —— 纯 FFmpeg 实现，零 Python 包依赖

功能：
  1. 动态地标字幕   → FFmpeg drawtext 滤镜
  2. 丝滑交叉淡化   → FFmpeg xfade 滤镜
  3. 自适应循环 BGM → FFmpeg stream_loop + amix
  4. 无音频 clip 处理 → 自动注入静音轨，确保 BGM 正常叠加
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# BGM 文件路径（project_root/test_assets/default_bgm.mp3）
_BGM_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test_assets", "default_bgm.mp3")
)

FADE_DUR = 1.0   # 交叉淡化时长（秒）
BGM_VOL  = 0.3   # BGM 音量系数


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def _get_duration(path: str) -> float:
    """通过 ffprobe 获取视频/音频时长（秒）"""
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _has_audio(path: str) -> bool:
    """检测视频文件是否包含音频轨道。Veo 生成的 clip 通常没有音频。"""
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "a",
         "-show_entries", "stream=index",
         "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        return len(json.loads(result.stdout).get("streams", [])) > 0
    except Exception:
        return False


def _run(cmd: list[str], label: str) -> subprocess.CompletedProcess:
    """运行 FFmpeg 命令，失败时记录日志并返回结果。"""
    logger.info(f"[Stitcher/{label}] {' '.join(cmd[:6])} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"[Stitcher/{label}] FAILED:\n{result.stderr[-800:]}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 主拼接函数（保持与旧版相同的函数签名）
# ─────────────────────────────────────────────────────────────────────────────

def stitch_clips_moviepy(
    local_files: list[str],
    landmark_names: Optional[list[str]] = None,
    output_path: str = "/tmp/final_vlog.mp4",
) -> str:
    """
    使用纯 FFmpeg 拼接视频，支持字幕、交叉淡化和 BGM。
    自动处理无音频的 Veo 视频片段（注入静音轨）。
    """
    if not local_files:
        raise RuntimeError("无可拼接的视频片段。")

    work_dir = tempfile.mkdtemp(prefix="stitcher_")
    logger.info(f"[Stitcher] 工作目录: {work_dir}, 片段数: {len(local_files)}")

    try:
        # ── 步骤 1：为每个片段叠加字幕、统一分辨率，并确保有音频轨 ──────
        processed: list[str] = []
        durations: list[float] = []

        for i, path in enumerate(local_files):
            out = os.path.join(work_dir, f"sub_{i:03d}.mp4")
            name = (landmark_names[i] if landmark_names and i < len(landmark_names) else "") or ""
            dur = _get_duration(path)
            has_audio = _has_audio(path)

            logger.info(f"[Stitcher] clip {i}: duration={dur:.2f}s, has_audio={has_audio}")

            # 视频滤镜：强制 1920×1080 letterbox
            vf = (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
            )
            if name:
                safe = name.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:")
                vf += (
                    f",drawtext=text='{safe}'"
                    f":fontsize=52:fontcolor=white"
                    f":borderw=3:bordercolor=black@0.8"
                    f":x=40:y=h-th-50"
                    f":enable='between(t,0,3)'"
                )

            if has_audio:
                # Clip 自带音频：直接处理
                cmd = [
                    "ffmpeg", "-y", "-i", path,
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2",
                    "-movflags", "+faststart",
                    out,
                ]
            else:
                # Clip 无音频（Veo 生成）：注入静音轨
                cmd = [
                    "ffmpeg", "-y",
                    "-i", path,
                    "-f", "lavfi", "-i", f"aevalsrc=0:channel_layout=stereo:sample_rate=44100:duration={dur:.4f}",
                    "-filter_complex", f"[0:v]{vf}[v]",
                    "-map", "[v]",
                    "-map", "1:a",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2",
                    "-movflags", "+faststart",
                    out,
                ]

            r = _run(cmd, f"subtitle-{i}")
            if r.returncode == 0 and os.path.exists(out):
                processed.append(out)
            else:
                # 降级：仅统一分辨率，保证有静音
                logger.warning(f"[Stitcher] subtitle pass 失败，降级处理 clip {i}")
                out_fallback = os.path.join(work_dir, f"raw_{i:03d}.mp4")
                fallback_cmd = [
                    "ffmpeg", "-y",
                    "-i", path,
                    "-f", "lavfi", "-i", f"aevalsrc=0:channel_layout=stereo:sample_rate=44100:duration={dur:.4f}",
                    "-filter_complex",
                    "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2",
                    out_fallback,
                ]
                if has_audio:
                    # 有音频就用简单编码
                    fallback_cmd = [
                        "ffmpeg", "-y", "-i", path,
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2",
                        out_fallback,
                    ]
                _run(fallback_cmd, f"resize-fallback-{i}")
                processed.append(out_fallback if os.path.exists(out_fallback) else path)

            durations.append(_get_duration(processed[-1]))

        # ── 步骤 2：拼接（xfade 交叉淡化，若失败则 concat 降级）────────────
        if len(processed) == 1:
            xfade_out = processed[0]
        else:
            xfade_out = os.path.join(work_dir, "xfade.mp4")
            success = _try_xfade(processed, durations, xfade_out)
            if not success:
                logger.info("[Stitcher] xfade 失败，降级为简单 concat")
                xfade_out = os.path.join(work_dir, "concat.mp4")
                _simple_concat(processed, xfade_out, work_dir)

        # ── 步骤 3：混入 BGM ─────────────────────────────────────────────────
        _mix_bgm(xfade_out, output_path)

        logger.info(f"[Stitcher] ✅ 完成: {output_path}")
        return output_path

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 内部辅助
# ─────────────────────────────────────────────────────────────────────────────

def _try_xfade(clips: list[str], durations: list[float], output: str) -> bool:
    """
    用 FFmpeg filter_complex xfade 链拼接 N 个片段。
    经过步骤1处理的 clip 均带有音频轨。
    成功返回 True，失败返回 False。
    """
    n = len(clips)
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", c]

    offsets: list[float] = []
    acc = 0.0
    for i in range(n - 1):
        acc += durations[i] - FADE_DUR
        offsets.append(max(acc, 0.01))

    filter_parts: list[str] = []
    prev_v = "[0:v]"
    for i, offset in enumerate(offsets):
        next_v = f"[vx{i}]" if i < len(offsets) - 1 else "[vout]"
        filter_parts.append(
            f"{prev_v}[{i+1}:v]xfade=transition=fade"
            f":duration={FADE_DUR}:offset={offset:.4f}{next_v}"
        )
        prev_v = next_v

    # 音频 concat（步骤1已保证每个 clip 有静音轨）
    audio_in = "".join(f"[{j}:a]" for j in range(n))
    filter_parts.append(f"{audio_in}concat=n={n}:v=0:a=1[aout]")

    filter_complex = ";".join(filter_parts)
    r = _run(
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            output,
        ],
        "xfade",
    )
    return r.returncode == 0 and os.path.exists(output)


def _simple_concat(clips: list[str], output: str, work_dir: str) -> None:
    """FFmpeg concat demuxer 无转场拼接（兜底方案）。"""
    list_path = os.path.join(work_dir, "concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    _run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            output,
        ],
        "concat-fallback",
    )


def _mix_bgm(video_path: str, output_path: str) -> None:
    """
    将 BGM 循环混入视频。
    - 若视频有音频轨：BGM 30% 音量与原声 amix
    - 若视频无音频轨：BGM 直接作为唯一音轨
    - 无 BGM 文件时复制原视频
    """
    if not os.path.isfile(_BGM_PATH):
        logger.info(f"[Stitcher] 未找到 BGM ({_BGM_PATH})，跳过")
        shutil.copy2(video_path, output_path)
        return

    total = _get_duration(video_path)
    video_has_audio = _has_audio(video_path)
    logger.info(f"[Stitcher] BGM 混入: total={total:.2f}s, video_has_audio={video_has_audio}")

    if video_has_audio:
        # 原声 + BGM 混合
        audio_filter = (
            f"[1:a]volume={BGM_VOL},atrim=0:{total:.4f},asetpts=PTS-STARTPTS[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        # 无原声：BGM 单独作为音轨
        audio_filter = (
            f"[1:a]volume={BGM_VOL},atrim=0:{total:.4f},asetpts=PTS-STARTPTS[aout]"
        )

    r = _run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", _BGM_PATH,
            "-filter_complex", audio_filter,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.4f}",
            "-movflags", "+faststart",
            output_path,
        ],
        "bgm-mix",
    )
    if r.returncode != 0 or not os.path.exists(output_path):
        logger.warning("[Stitcher] BGM 混入失败，直接复制原视频")
        shutil.copy2(video_path, output_path)
