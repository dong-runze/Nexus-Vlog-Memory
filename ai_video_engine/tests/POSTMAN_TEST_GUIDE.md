# AI Video Engine API 测试文档

## 基础信息

| 项目 | 值 |
|------|-----|
| 基础 URL | http://localhost:8001 |
| API Key | dev-api-key-12345 |
| Swagger 文档 | http://localhost:8001/docs |

---

## 全局 Headers

除公开接口外，所有请求需要添加：

| Header | Value |
|--------|-------|
| X-API-Key | dev-api-key-12345 |
| Content-Type | application/json |

---

## 1. 健康检查接口（公开）

### GET /api/v1/health

**说明**: 检查服务状态，无需 API Key

**请求示例**:
```
GET http://localhost:8001/api/v1/health
```

**预期响应**:
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "status": "warning",
        "missing_config": ["WAVESPEED_API_KEY", "INSFORGE_API_KEY", "INSFORGE_PROJECT_URL"]
    }
}
```

---

## 2. 身份验证测试

### 2.1 无 API Key 访问

**请求示例**:
```
POST http://localhost:8001/api/v1/stitch-vlog
Content-Type: application/json

{
    "video_urls": ["https://example.com/test.mp4"]
}
```

**预期响应**:
```json
{
    "code": 401,
    "message": "无效的 API Key",
    "data": null
}
```

### 2.2 错误 API Key 访问

**请求示例**:
```
POST http://localhost:8001/api/v1/stitch-vlog
X-API-Key: wrong-key
Content-Type: application/json

{
    "video_urls": ["https://example.com/test.mp4"]
}
```

**预期响应**:
```json
{
    "code": 401,
    "message": "无效的 API Key",
    "data": null
}
```

### 2.3 正确 API Key 访问

**请求示例**:
```
POST http://localhost:8001/api/v1/stitch-vlog
X-API-Key: dev-api-key-12345
Content-Type: application/json

{
    "video_urls": ["https://example.com/test.mp4"]
}
```

**预期响应**:
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "message": "视频拼接任务已提交，共 1 个片段"
    }
}
```

---

## 3. 视频拼接接口

### 3.1 提交视频拼接任务

**接口**: POST /api/v1/stitch-vlog

**请求示例**:
```
POST http://localhost:8001/api/v1/stitch-vlog
X-API-Key: dev-api-key-12345
Content-Type: application/json

{
    "video_urls": [
        "https://www.w3schools.com/html/mov_bbb.mp4",
        "https://www.w3schools.com/html/movie.mp4"
    ]
}
```

**预期响应**:
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "message": "视频拼接任务已提交，共 2 个片段"
    }
}
```

### 3.2 错误请求 - 空 URL 列表

**请求示例**:
```
POST http://localhost:8001/api/v1/stitch-vlog
X-API-Key: dev-api-key-12345
Content-Type: application/json

{
    "video_urls": []
}
```

**预期响应**:
```json
{
    "code": 400,
    "message": "至少需要一个有效的视频 URL",
    "data": null
}
```

---

## 4. 任务状态查询接口

### 4.1 查询存在的任务

**接口**: GET /task/{taskId}/status

**请求示例**:
```
GET http://localhost:8001/task/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
X-API-Key: dev-api-key-12345
```

**预期响应** (处理中):
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "task_type": "video_stitch",
        "status": "processing",
        "progress": 45,
        "total": 120,
        "result": null,
        "error": null,
        "created_at": "2026-02-27T10:30:00.123456",
        "updated_at": "2026-02-27T10:30:05.456789",
        "estimated_time_remaining": 30,
        "metadata": {
            "video_urls": ["https://..."]
        },
        "resolution": "1920x1080",
        "bitrate": "5M",
        "duration": 10.5,
        "clip_count": 2
    }
}
```

**预期响应** (已完成):
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "task_type": "video_stitch",
        "status": "completed",
        "progress": 100,
        "total": 120,
        "result": "{\"output_path\": \"...\", \"resolution\": \"1920x1080\", \"bitrate\": \"5M\", \"duration\": 10.5, \"clip_count\": 2}",
        "error": null,
        "created_at": "2026-02-27T10:30:00.123456",
        "updated_at": "2026-02-27T10:30:15.123456",
        "estimated_time_remaining": 0,
        "metadata": {
            "video_urls": ["https://..."]
        },
        "resolution": "1920x1080",
        "bitrate": "5M",
        "duration": 10.5,
        "clip_count": 2
    }
}
```

### 4.2 查询不存在的任务

**请求示例**:
```
GET http://localhost:8001/task/not-exist-task-id/status
X-API-Key: dev-api-key-12345
```

**预期响应**:
```json
{
    "detail": "任务 not-exist-task-id 不存在"
}
```

---

## 5. 视频生成接口

### 5.1 提交视频生成任务

**接口**: POST /api/v1/generate-clip

**请求示例**:
```
POST http://localhost:8001/api/v1/generate-clip
X-API-Key: dev-api-key-12345
Content-Type: application/json

{
    "prompt": "A thrilling roller coaster ride at the amusement park"
}
```

**预期响应**:
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "message": "视频片段生成任务已提交"
    }
}
```

**注意**: 由于未配置 WAVESPEED_API_KEY，任务会失败，状态会变为 "failed"

### 5.2 查询视频生成任务状态

**请求示例**:
```
GET http://localhost:8001/task/b2c3d4e5-f6a7-8901-bcde-f12345678901/status
X-API-Key: dev-api-key-12345
```

**预期响应** (失败):
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "task_type": "video_clip",
        "status": "failed",
        "progress": 50,
        "total": 100,
        "result": null,
        "error": "WaveSpeed AI 调用失败: ...",
        "created_at": "2026-02-27T10:35:00.123456",
        "updated_at": "2026-02-27T10:35:10.123456",
        "estimated_time_remaining": null,
        "metadata": {
            "prompt": "A cinematic, vibrant vlog-style video clip...",
            "original_prompt": "A thrilling roller coaster ride at the amusement park"
        }
    }
}
```

### 5.3 错误请求 - 空 prompt

**请求示例**:
```
POST http://localhost:8001/api/v1/generate-clip
X-API-Key: dev-api-key-12345
Content-Type: application/json

{
    "prompt": ""
}
```

**预期响应**:
```json
{
    "code": 400,
    "message": "prompt 不能为空",
    "data": null
}
```

---

## 6. 限流测试

### 6.1 测试限流

**说明**: 默认每分钟 100 次请求，短时间内发送大量请求会触发限流

**请求示例**: 快速连续发送 50+ 个请求

**预期响应** (触发限流后):
```json
{
    "code": 429,
    "message": "请求过于频繁，请稍后再试",
    "data": null
}
```

---

## 完整测试流程

1. **健康检查** → GET /api/v1/health
2. **身份验证测试** → 无 Key、错误 Key 访问
3. **提交拼接任务** → POST /api/v1/stitch-vlog（保存返回的 task_id）
4. **轮询状态** → GET /task/{taskId}/status（等待完成）
5. **提交生成任务** → POST /api/v1/generate-clip（保存返回的 task_id）
6. **查询生成状态** → GET /task/{taskId}/status
7. **测试错误情况** → 空列表、不存在的任务 ID
