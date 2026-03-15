"""
services/firestore_client.py
使用 Google Cloud Firestore 作为地标数据的持久化存储。
支持 Multi-location: 所有函数均含 location_id 参数，查询与写入均以 location_id 隔离。
"""

import os
from google.cloud import firestore

# 初始化 Firestore 客户端
# 将自动使用 GOOGLE_APPLICATION_CREDENTIALS 提供的 ADC 凭证
try:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        db = firestore.AsyncClient(project=project_id)
        print(f"[Firestore] Async Client initialized for project: {project_id}")
    else:
        db = firestore.AsyncClient()
        print("[Firestore] Async Client initialized using default project from ADC")
except Exception as e:
    print(f"[Warning] Failed to initialize Firestore client: {e}")
    db = None

COLLECTION_NAME = "landmarks"

async def get_all_landmarks(room_code: str = "master", location_id: str = "USS") -> list[dict]:
    """获取指定房间 & 地点的所有地标数据（Merge-on-Read 策略）"""
    if not db:
        raise RuntimeError("Firestore client not initialized")
    
    try:
        # 第一步：获取所有 "基础底座" 数据 (is_user_created == False)，并按 location_id 过滤
        master_docs = (
            db.collection(COLLECTION_NAME)
            .where("location_id", "==", location_id)
            .where("is_user_created", "==", False)
            .stream()
        )
        merged_data = {}
        async for doc in master_docs:
            data = doc.to_dict()
            real_id = data.get('id') or doc.id
            data['id'] = real_id
            merged_data[real_id] = data

        print(f"[DEBUG] location={location_id} | Master 房间加载了 {len(merged_data)} 个底座地标")

        # 第二步：获取当前用户房间的所有沙盒数据，并按 location_id 过滤
        if room_code == "master":
            result = [v for v in merged_data.values() if not v.get("is_deleted")]
            print(f"[DEBUG] 最终返回前端的 master 地标数量: {len(result)}")
            return result

        user_docs = (
            db.collection(COLLECTION_NAME)
            .where("location_id", "==", location_id)
            .where("is_user_created", "==", True)
            .where("room_code", "==", room_code)
            .stream()
        )
            
        async for doc in user_docs:
            user_data = doc.to_dict()
            real_id = user_data.get('id') or doc.id
            user_data['id'] = real_id
            
            doc_id = real_id
            
            # 处理墓碑：如果用户删除了这个地标，从合并字典中彻底拔除
            if user_data.get("is_deleted") == True:
                merged_data.pop(doc_id, None)
                continue
                
            # 处理合并与新增
            if doc_id in merged_data:
                merged_data[doc_id].update(user_data)
            else:
                merged_data[doc_id] = user_data

        result = list(merged_data.values())
        print(f"[DEBUG] 最终返回前端的 {room_code}@{location_id} 房间地标数量: {len(result)}")
        return result
    except Exception as e:
        print(f"[Firestore] Error getting landmarks: {e}")
        raise


async def delete_landmark(landmark_id: str, room_code: str = "master", location_id: str = "USS") -> dict:
    """删除或标记删除单个地标数据，支持沙盒墓碑机制"""
    if not db:
        raise RuntimeError("Firestore client not initialized")
        
    try:
        if room_code == "master":
            # 主房间：直接物理删除
            doc_id = landmark_id
            await db.collection(COLLECTION_NAME).document(doc_id).delete()
            return {"status": "deleted", "id": landmark_id, "room": "master", "location_id": location_id}
        else:
            # 用户沙盒房间：使用墓碑机制，不真删
            doc_id = f"{room_code}_{landmark_id}"
            tombstone_data = {
                "id": landmark_id,
                "is_deleted": True,
                "room_code": room_code,
                "is_user_created": True,
                "location_id": location_id,
            }
            await db.collection(COLLECTION_NAME).document(doc_id).set(tombstone_data, merge=True)
            return {"status": "tombstoned", "id": landmark_id, "room": room_code, "location_id": location_id}
    except Exception as e:
        print(f"[Firestore] Error deleting landmark {landmark_id}: {e}")
        raise


async def get_vlogs_by_room(room_code: str = "master", location_id: str = "USS") -> list[dict]:
    """获取指定房间 & 地点的合成记录"""
    if not db:
        raise RuntimeError("Firestore client not initialized")
        
    try:
        final_list = []
        
        # 1. 获取 master 的 Vlog 记录（按 location_id 过滤）
        master_docs = (
            db.collection("vlogs")
            .where("location_id", "==", location_id)
            .where("room_code", "==", "master")
            .stream()
        )
        async for doc in master_docs:
            final_list.append(doc.to_dict())
            
        # 2. 如果不是 master，获取用户沙盒的 Vlog 记录（按 location_id 过滤）
        if room_code != "master":
            user_docs = (
                db.collection("vlogs")
                .where("location_id", "==", location_id)
                .where("room_code", "==", room_code)
                .stream()
            )
            async for doc in user_docs:
                final_list.append(doc.to_dict())
                
        # 按照创建时间降序排序
        final_list.sort(key=lambda x: x.get("created_at", x.get("timestamp", 0)), reverse=True)
        return final_list
            
    except Exception as e:
        print(f"[Firestore] Error getting vlog history for room {room_code}@{location_id}: {e}")
        raise


async def save_landmark(landmark_id: str, data: dict, room_code: str = "master", location_id: str = "USS") -> dict:
    """保存或更新单个地标数据，实现沙盒隔离，生成高可读性 Slug Document ID"""
    if not db:
        raise RuntimeError("Firestore client not initialized")

    try:
        # 解析 Pydantic 模型（防御性设计）
        if hasattr(data, 'model_dump'):
            save_data = data.model_dump()
        else:
            save_data = dict(data)

        # 强制写入 room_code 和 location_id
        save_data['room_code'] = room_code
        save_data['location_id'] = location_id

        # 确保 featuresEn / featuresZh 有默认值，防止 Schema 塌陷
        if not save_data.get('featuresEn'):
            save_data['featuresEn'] = []
        if not save_data.get('featuresZh'):
            save_data['featuresZh'] = []

        # ── 高可读性 Slug Document ID ─────────────────────────────────────
        # 优先从 name (英文) 生成 slug；退而求其次用传入的 landmark_id
        raw_name = (
            save_data.get("name")          # 前端 English name
            or save_data.get("name_en")    # 可能的别名字段
            or landmark_id
        )
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', raw_name.strip().lower()).strip('_')
        slug = slug[:60]  # 限制长度，Firestore 文档 ID 上限 1500 字节，保守截断

        if room_code == "master":
            doc_id = f"master_{location_id}_{slug}"
            save_data["is_user_created"] = False
        else:
            doc_id = f"{room_code}_{location_id}_{slug}"
            save_data["is_user_created"] = True

        # 把最终 doc_id 写回文档内部的 id 字段，确保前端读到一致的 ID
        save_data['id'] = doc_id

        print(f"[Firestore] Saving doc_id='{doc_id}' (room={room_code}, location={location_id})")

        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
        await doc_ref.set(save_data, merge=True)

        return save_data
    except Exception as e:
        print(f"[Firestore] Error saving landmark {landmark_id}: {e}")
        raise
