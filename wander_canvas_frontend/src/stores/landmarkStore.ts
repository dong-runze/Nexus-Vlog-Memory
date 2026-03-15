import { reactive } from 'vue'
import type { Landmark, LandmarkCategory } from '../types/landmark'
import { DEFAULT_LANDMARKS } from '../types/landmark'

export interface VlogData {
  vlog_id: string
  video_url: string
  title?: string
  created_at?: number
  duration?: number
  clip_count?: number
  room_code?: string
}

// ===================== Multi-location 配置字典 =====================
// 新增景点时，在此处增加一条记录即可实现全局联动
export const LOCATION_CONFIG: Record<string, { label: string; center: [number, number]; zoom: number }> = {
  USS: {
    label: 'Universal Studios Singapore',
    center: [1.2540, 103.8238],
    zoom: 17,
  },
  Tokyo_Disney: {
    label: 'Tokyo Disneyland',
    center: [35.6329, 139.8804],
    zoom: 16,
  },
  Forbidden_City: {
    label: '故宫 Forbidden City',
    center: [39.9163, 116.3972],
    zoom: 16,
  },
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const ALL_CATEGORIES: LandmarkCategory[] = ['landmark', 'school', 'dining', 'special']
const STORAGE_KEY = 'uss-landmarks'
const ROOM_CODE_KEY = 'vlog_room_code'
const LOCATION_KEY = 'vlog_location_id'

function loadRoomCode(): string {
  try {
    const stored = localStorage.getItem(ROOM_CODE_KEY)
    if (stored) return stored
  } catch (e) {
    console.warn('Failed to load room code:', e)
  }
  return 'master'
}

function loadLocationId(): string {
  try {
    const stored = localStorage.getItem(LOCATION_KEY)
    if (stored && LOCATION_CONFIG[stored]) return stored
  } catch (e) {
    console.warn('Failed to load location id:', e)
  }
  return 'USS'
}

function loadFromStorage(): Landmark[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (e) {
    console.warn('Failed to load from localStorage:', e)
  }
  return [...DEFAULT_LANDMARKS]
}

function saveToStorage(landmarks: Landmark[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(landmarks))
  } catch (e) {
    console.warn('Failed to save to localStorage:', e)
  }
}

/**
 * 向自建后端（进而存入 Firestore）同步单个节点数据。
 * payload 中含 location_id，实现多地点隔离。
 */
async function saveToCloud(landmark: Landmark, roomCode: string, locationId: string): Promise<void> {
  const payload = {
    id: landmark.id,
    name: landmark.name,
    name_zh: landmark.nameZh,
    category: landmark.category,
    lat: landmark.lat,
    lng: landmark.lng,
    image_url: landmark.imageUrl,
    video_url: landmark.videoUrl,
    opening_hours: landmark.openingHours,
    introduction: landmark.introduction,
    introduction_zh: landmark.introductionZh,
    is_user_created: landmark.isUserCreated,
    ai_narration_zh: landmark.aiNarrationZh,
    ai_narration_en: landmark.aiNarrationEn,
    ai_video_prompt: landmark.aiVideoPrompt,
    user_video_prompt: landmark.userVideoPrompt,
    user_video_prompt_zh: landmark.userVideoPromptZh,
    coordinates: landmark.coordinates,
    featuresEn: landmark.featuresEn ?? [],   // 保证不传 undefined，确保 Schema 不塌陷
    featuresZh: landmark.featuresZh ?? [],   // 同上
    room_code: roomCode,
    location_id: locationId, // [Multi-location]
  }
  
  console.log('[Firestore Sync] Saving payload:', payload)
  
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/landmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (!res.ok) {
        const errorData = await res.json()
        console.error('[Firestore Sync] Save error:', errorData)
        alert(`保存到云端失败: ${errorData.detail || errorData.message || 'Unknown error'}`)
        return
    }
    
    const data = await res.json()
    console.log('[Firestore Sync] Save success:', data)
  } catch (e) {
    console.error('[Firestore Sync] Network error:', e)
  }
}

/**
 * 从云端（Firestore）删除或标记删除（墓碑机制）单个节点数据。
 */
async function deleteFromCloud(landmarkId: string, roomCode: string, locationId: string): Promise<void> {
  console.log(`[Firestore Sync] Deleting landmark ${landmarkId} (room: ${roomCode}, location: ${locationId})...`)
  
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/landmarks/${landmarkId}?room_code=${roomCode}&location_id=${locationId}`,
      { method: 'DELETE' }
    )
    
    if (!res.ok) {
        const errorData = await res.json()
        console.error('[Firestore Sync] Delete error:', errorData)
        alert(`从云端删除失败: ${errorData.detail || errorData.message || 'Unknown error'}`)
        return
    }
    
    const data = await res.json()
    console.log('[Firestore Sync] Delete success:', data)
  } catch (e) {
    console.error('[Firestore Sync] Network error during deletion:', e)
  }
}

/**
 * 从自建后端（Firestore）加载所有地标数据，按 room_code + location_id 隔离。
 */
async function loadAllFromCloud(roomCode: string, locationId: string): Promise<Landmark[]> {
  console.log(`[Firestore Sync] Loading landmarks from cloud (room=${roomCode}, location=${locationId})...`)
  
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/landmarks?room_code=${roomCode}&location_id=${locationId}`)
    if (!res.ok) {
      console.error('[Firestore Sync] Load error:', res.status)
      return []
    }
    
    const json = await res.json()
    const data = json.data
    
    if (!data || data.length === 0) {
      console.log('[Firestore Sync] No data found in cloud')
      return []
    }
    
    console.log('[Firestore Sync] Loaded raw data:', data)

    // 防御性过滤：剩童药墓碑记录，即使后端已过滤这些记录
    const ghosts = data.filter((row: any) => row.is_deleted)
    if (ghosts.length > 0) {
      console.warn(`[Firestore Sync] 警告：发现 ${ghosts.length} 条墓碑记录漏通到前端，已静默过滤`)
    }
    // 同时过滤：is_deleted、id 为空、lat 和 lng 同时为 0 的幽灵记录
    const cleanData = data.filter((row: any) => {
      if (row.is_deleted) return false
      if (!row.id) return false
      // lat/lng 都为 0 说明是未初始化的占位数据（Firestore 写入失败的幽灵）
      const lat = parseFloat(row.lat) || 0
      const lng = parseFloat(row.lng) || 0
      if (lat === 0 && lng === 0) {
        console.warn(`[Firestore Sync] 过滤掉 0,0 坐标幽灵地标: id=${row.id}, name=${row.name}`)
        return false
      }
      return true
    })

    // 将数据库字段映射回前端 Landmark 类型
    return cleanData.map((row: any) => ({
      id: row.id,
      name: row.name || '',
      nameZh: row.name_zh || row.nameZh || '',
      category: row.category || 'landmark',
      lat: parseFloat(row.lat) || 0,
      lng: parseFloat(row.lng) || 0,
      imageUrl: row.image_url || row.imageUrl || undefined,
      videoUrl: row.video_url || row.videoUrl || undefined,
      videoBlobName: row.videoBlobName || row.video_blob_name || undefined,
      openingHours: row.opening_hours || row.openingHours || undefined,
      introduction: row.introduction || undefined,
      introductionZh: row.introduction_zh || row.introductionZh || undefined,
      features: row.features || undefined,
      featuresEn: row.featuresEn || row.features_en || undefined,
      featuresZh: row.featuresZh || row.features_zh || undefined,
      isUserCreated: row.is_user_created || row.isUserCreated || false,
      aiNarrationZh: row.ai_narration_zh || row.aiNarrationZh || undefined,
      aiNarrationEn: row.ai_narration_en || row.aiNarrationEn || undefined,
      aiVideoPrompt: row.ai_video_prompt || row.aiVideoPrompt || undefined,
      userVideoPrompt: row.user_video_prompt || row.userVideoPrompt || undefined,
      userVideoPromptZh: row.user_video_prompt_zh || row.userVideoPromptZh || undefined,
      coordinates: row.coordinates || undefined
    } as Landmark))
  } catch (e) {
    console.error('[Firestore Sync] Load network error:', e)
    return []
  }
}

const initialLocationId = loadLocationId()

export const store = reactive({
  // 初始值绝对为空数组，云端数据是唯一权威来源。
  // 使用 loadFromStorage() 初始化会导致 DEFAULT_LANDMARKS 或旧脏数据在云端加载完成前短暂显示。
  landmarks: [] as Landmark[],
  roomCode: loadRoomCode(),
  currentLocation: initialLocationId,  // [Multi-location] 当前景点 ID
  // 地图飞行目标配置（Map.vue 监听此值来触发 flyTo）
  mapTargetConfig: { ...LOCATION_CONFIG[initialLocationId] } as { label: string; center: [number, number]; zoom: number } | null,
  selectedLandmark: null as Landmark | null,
  isDetailPanelOpen: false,
  isEditorModalOpen: false,
  editingLandmark: null as Landmark | null,
  activeCategories: [...ALL_CATEGORIES] as LandmarkCategory[],
  searchQuery: '',
  globalVlogUrl: '',
  vlogHistory: [] as VlogData[],
  
  setLandmarks(landmarks: Landmark[]) {
    this.landmarks = [...landmarks]
    saveToStorage(this.landmarks)
  },

  addLandmark(landmark: Landmark) {
    this.landmarks = [...this.landmarks, landmark]
    saveToStorage(this.landmarks)
    saveToCloud(landmark, this.roomCode, this.currentLocation)
  },

  cloneLandmark(landmark: Landmark, offsetLat: number = 0.0002, offsetLng: number = 0.0002): Landmark {
    const cloned: Landmark = {
      ...landmark,
      id: `clone-${Date.now()}`,
      lat: landmark.lat + offsetLat,
      lng: landmark.lng + offsetLng,
      isUserCreated: true,
      videoUrl: undefined,
      aiNarrationZh: undefined,
      aiNarrationEn: undefined,
      aiVideoPrompt: undefined
    }
    this.landmarks = [...this.landmarks, cloned]
    saveToStorage(this.landmarks)
    saveToCloud(cloned, this.roomCode, this.currentLocation)
    return cloned
  },

  updateLandmark(id: string, updates: Partial<Landmark>) {
    const existing = this.landmarks.find(l => l.id === id)
    if (existing) {
      const merged = { ...existing, ...updates }
      this.landmarks = this.landmarks.map(l => 
        l.id === id ? merged : l
      )
      if (this.selectedLandmark?.id === id) {
        this.selectedLandmark = merged
      }
      saveToStorage(this.landmarks)
    }
  },

  updateLandmarkPreserveCoords(id: string, updates: Partial<Omit<Landmark, 'lat' | 'lng'>>) {
    const existing = this.landmarks.find(l => l.id === id)
    if (existing) {
      const merged = { ...existing, ...updates }
      this.landmarks = this.landmarks.map(l => 
        l.id === id ? merged : l
      )
      if (this.selectedLandmark?.id === id) {
        this.selectedLandmark = merged
      }
      saveToStorage(this.landmarks)
      saveToCloud(merged, this.roomCode, this.currentLocation)
    }
  },

  updateLandmarkSilent(id: string, lat: number, lng: number) {
    const landmark = this.landmarks.find(l => l.id === id)
    if (landmark && (landmark.lat !== lat || landmark.lng !== lng)) {
      this.landmarks = this.landmarks.map(l => 
        l.id === id ? { ...l, lat, lng } : l
      )
      if (this.selectedLandmark?.id === id) {
        this.selectedLandmark = { ...this.selectedLandmark, lat, lng }
      }
      saveToStorage(this.landmarks)
    }
  },

  deleteLandmark(id: string) {
    this.landmarks = this.landmarks.filter(l => l.id !== id)
    if (this.selectedLandmark?.id === id) {
      this.selectedLandmark = null
      this.isDetailPanelOpen = false
    }
    saveToStorage(this.landmarks)
    deleteFromCloud(id, this.roomCode, this.currentLocation)
  },

  selectLandmark(landmark: Landmark | null) {
    this.selectedLandmark = landmark
    this.isDetailPanelOpen = landmark !== null
    // 点击地标时，触发地图飞行至该地标坐标
    if (landmark) {
      this.mapTargetConfig = {
        label: landmark.nameZh || landmark.name,
        center: [landmark.lat, landmark.lng],
        zoom: 19,
      }
    }
  },

  openDetailPanel() {
    this.isDetailPanelOpen = true
  },

  closeDetailPanel() {
    this.isDetailPanelOpen = false
  },

  openEditorModal(landmark?: Landmark) {
    this.isEditorModalOpen = true
    this.editingLandmark = landmark || null
  },

  closeEditorModal() {
    this.isEditorModalOpen = false
    this.editingLandmark = null
  },

  toggleCategory(category: LandmarkCategory) {
    if (this.activeCategories.includes(category)) {
      this.activeCategories = this.activeCategories.filter(c => c !== category)
    } else {
      this.activeCategories = [...this.activeCategories, category]
    }
  },

  setSearchQuery(query: string) {
    this.searchQuery = query
  },

  changeRoomCode(newCode: string) {
    this.roomCode = newCode || 'master'
    localStorage.setItem(ROOM_CODE_KEY, this.roomCode)
    this.loadFromCloud()
    this.loadVlogFromCloud()
  },

  /**
   * [Auto-Seed] 当新地点没有任何数据时，自动在地图中心附近4个空占位地标并同步到 Firestore。
   */
  async seedEmptyLandmarks(lat: number, lng: number, locationId: string) {
    const offsets: [number, number][] = [
      [ 0.002,  0.002],
      [-0.002, -0.002],
      [ 0.002, -0.002],
      [-0.002,  0.002],
    ]

    console.log(`[AutoSeed] 开始拓荒——地点: "${locationId}" 坐标中心: [${lat}, ${lng}]`)

    for (let i = 0; i < offsets.length; i++) {
      const seedLat = +(lat + offsets[i][0]).toFixed(5)
      const seedLng = +(lng + offsets[i][1]).toFixed(5)
      const payload = {
        id:              `placeholder_${Date.now()}_${i}`,  // 后端会用英文名生成 slug
        name:            `New Landmark ${i + 1}`,
        name_zh:         `新地标 ${i + 1}`,
        location_id:     locationId,
        room_code:       this.roomCode,
        category:        'landmark',
        lat:             seedLat,
        lng:             seedLng,
        coordinates:     `${seedLat}, ${seedLng}`,
        // 同时发驼虹式 + 闾式，确保后端而就近的字段都能命中
        features_en:     [] as string[],
        features_zh:     [] as string[],
        featuresEn:      [] as string[],
        featuresZh:      [] as string[],
        opening_hours:   '09:00 AM - 06:00 PM',
        introduction:    'Click edit to update this landmark.',
        introduction_zh: '点击编辑以更新此地标信息。',
        image_url:       '',
        user_video_prompt: '',
        video_url:       '',
        ai_narration_en: '',
        ai_narration_zh: '',
        is_user_created: true,
      }

      try {
        console.log(`[AutoSeed] 发送占位地标 ${i + 1} payload:`, JSON.stringify(payload))
        const res = await fetch(`${BACKEND_URL}/api/v1/landmarks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })

        if (res.ok) {
          const json = await res.json()
          console.log(`[AutoSeed] ✅ 占位地标 ${i + 1} 写入成功 [${seedLat}, ${seedLng}]`, json?.data?.id ?? '')
        } else {
          // 强制提取错误详情，当前。
          let errBody: unknown
          try { errBody = await res.json() } catch { errBody = await res.text() }
          console.error(
            `[AutoSeed] ❌ 占位地标 ${i + 1} 失败 HTTP ${res.status} (${res.statusText}):`,
            errBody
          )
        }
      } catch (e) {
        console.error(`[AutoSeed] ❌ 占位地标 ${i + 1} 网络异常:`, e)
      }
    }

    console.log('[AutoSeed] 拓荒完毕。')
  },

  /**
   * [Multi-location] 切换大景点，支持预设坐标与 Nominatim 动态地理编码。
   * - 预设地点：直接从 LOCATION_CONFIG 读取坐标并 flyTo。
   * - 自由输入：调用 OpenStreetMap Nominatim API 动态获取坐标再 flyTo。
   */
  async changeLocation(newLocationId: string) {
    if (!newLocationId) return

    // 先记录当前地点，出错可回滚
    const previousLocation = this.currentLocation

    this.currentLocation = newLocationId
    localStorage.setItem(LOCATION_KEY, newLocationId)

    // 情况 1：预设地点，有已知坐标
    if (LOCATION_CONFIG[newLocationId]) {
      this.mapTargetConfig = { ...LOCATION_CONFIG[newLocationId] }
      console.log(`[Location] Flying to preset: ${newLocationId}`)
    } else {
      // 情况 2：自由输入，向 Nominatim 查询坐标
      console.log(`[Location] Unknown preset, querying Nominatim for: "${newLocationId}"`)
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(newLocationId)}&limit=1`
        const res = await fetch(url, {
          headers: { 'Accept-Language': 'en', 'User-Agent': 'WanderCanvas/1.0' }
        })
        const data = await res.json()
        if (data && data.length > 0) {
          const lat = parseFloat(data[0].lat)
          const lon = parseFloat(data[0].lon)
          console.log(`[Location] Nominatim found: "${data[0].display_name}" → [${lat}, ${lon}]`)
          this.mapTargetConfig = {
            label: newLocationId,
            center: [lat, lon],
            zoom: 15,
          }
        } else {
          // 找不到地点：回滚状态，抛出错误让组件处理 UI
          console.warn(`[Location] Nominatim returned no results for: "${newLocationId}"`)
          this.currentLocation = previousLocation
          localStorage.setItem(LOCATION_KEY, previousLocation)
          throw new Error(`Location not found: "${newLocationId}"`)
        }
      } catch (e) {
        // 网络错误或上面主动抛出的错误一并回滚并再抛出
        if (this.currentLocation !== previousLocation) {
          this.currentLocation = previousLocation
          localStorage.setItem(LOCATION_KEY, previousLocation)
        }
        throw e   // 传播给调用方（Sidebar.vue「handleLocationSubmit）
      }
    }

    // 切换地点时先清空地标列表，防止旧地点数据（如 USS）残留到新地点（如 NTU）
    this.landmarks = []

    // 拉取云端数据；返回值直接反映云端是否为空（不依赖 this.landmarks.length）
    const hadCloudData = await this.loadFromCloud()
    this.loadVlogFromCloud()

    // 冷启动检测：直接用云端返回值判断，不被本地存储干扰
    if (!hadCloudData) {
      const center = this.mapTargetConfig?.center
      if (center && center.length >= 2) {
        const [seedLat, seedLng] = center
        console.log(`[AutoSeed] 地点 "${this.currentLocation}" 云端无数据，开始拓荒...`)
        await this.seedEmptyLandmarks(seedLat, seedLng, newLocationId)
        // 拓荒完成后再次拉取，确保前端拿到后端已生成的标准 Document ID
        await this.loadFromCloud()
      }
    }
  },

  isCategoryActive(category: LandmarkCategory): boolean {
    return this.activeCategories.includes(category)
  },

  getFilteredLandmarks(): Landmark[] {
    return this.landmarks.filter((landmark) => {
      const isActive = this.activeCategories.includes(landmark.category)
      const matchesSearch = this.searchQuery === '' ||
        landmark.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        landmark.nameZh.includes(this.searchQuery)
      return isActive && matchesSearch
    })
  },

  async loadFromCloud(): Promise<boolean> {
    // 强制清空前端状态，防止重复调用时数据叠加（幽灵标记 / Ghost markers）
    this.landmarks = []
    const cloudData = await loadAllFromCloud(this.roomCode, this.currentLocation)
    if (cloudData.length > 0) {
      this.landmarks = [...cloudData]
      saveToStorage(this.landmarks)
      console.log(`[Firestore Sync] Loaded ${cloudData.length} landmarks from cloud`)
      return true   // 云端有数据
    } else {
      console.log('[Firestore Sync] No cloud data, keeping empty state')
      saveToStorage([])
      return false  // 云端为空
    }
  },

  async loadVlogFromCloud(): Promise<void> {
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/v1/vlogs?room_code=${this.roomCode}&location_id=${this.currentLocation}`
      )
      if (!res.ok) return
      
      const json = await res.json()
      if (json.data && Array.isArray(json.data)) {
        this.vlogHistory = json.data
      } else {
        this.vlogHistory = []
      }
    } catch (e) {
      console.error('[Firestore Sync] Load vlog error:', e)
    }
  }
})

// Initialize values on start
store.loadFromCloud()
store.loadVlogFromCloud()
