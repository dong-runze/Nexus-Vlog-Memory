<script setup lang="ts">
import { ref, computed } from 'vue'
import { store, LOCATION_CONFIG } from '../stores/landmarkStore'
import type { Landmark, LandmarkCategory } from '../types/landmark'
import { CATEGORY_INFO } from '../types/landmark'
import { Search, Rocket, Star, IceCreamCone, Camera, Download, Upload, ChevronLeft, ChevronRight, Video, X, Loader2, MessageCircle, Film, Sparkles, Languages, MapPin } from 'lucide-vue-next'

const props = defineProps<{
  isCollapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'focus-landmark', landmark: Landmark): void
  (e: 'toggle'): void
}>()

const searchInput = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const newRoomCode = ref(store.roomCode)
const locationInput = ref(store.currentLocation)
const isExporting = ref(false)
const isImporting = ref(false)

// ── 影院级视频弹窗状态 ──────────────────────────────────────
const isVideoModalOpen = ref(false)
const currentPlayingVideoUrl = ref('')

function openVideoModal(videoUrl: string) {
  if (!videoUrl) return
  currentPlayingVideoUrl.value = videoUrl
  isVideoModalOpen.value = true
}

function closeVideoModal() {
  isVideoModalOpen.value = false
  // 清空 src 强制停止视频播放，防止 background audio 泄漏
  currentPlayingVideoUrl.value = ''
}

// ESC 键关闭弹窗
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isVideoModalOpen.value) closeVideoModal()
}
import { onMounted, onUnmounted } from 'vue'
onMounted(() => window.addEventListener('keydown', handleKeyDown))
onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))


function switchRoom() {
  const code = newRoomCode.value.trim()
  if (code && code !== store.roomCode) {
    store.changeRoomCode(code)
  }
}

function handleLocationConfirm() {
  const val = locationInput.value.trim()
  if (val) {
    store.changeLocation(val)
  }
}

async function handleLocationSubmit(event: Event) {
  const input = event.target as HTMLInputElement
  const val = input.value.trim()
  // 没有输入或和当前地点相同，富饱
  if (!val || val === store.currentLocation) return
  try {
    await store.changeLocation(val)
    locationInput.value = store.currentLocation
  } catch {
    alert(`Location not found: "${val}".\nPlease enter a valid city or attraction name.\n\n(无法定位该地点，请输入准确的城市或景点名称)`)
    // 强制重置输入框为当前有效地点，切断死循环
    input.value = store.currentLocation
    locationInput.value = store.currentLocation
  }
}

// --- Vlog 生成相关状态 ---
const isGenerating = ref(false)
const isGeneratingScript = ref(false)
const vlogScript = ref<any[]>([])
const isScriptZh = ref(false)
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
const INSFORGE_URL = import.meta.env.VITE_INSFORGE_URL || 'https://jkuxca49.ap-southeast.insforge.app'
const INSFORGE_ANON_KEY = import.meta.env.VITE_INSFORGE_ANON_KEY || ''

const categories: LandmarkCategory[] = ['landmark', 'school', 'dining', 'special']

const iconMap = {
  landmark: Rocket,
  school: Star,
  dining: IceCreamCone,
  special: Camera
}

const filteredLandmarks = computed(() => {
  return store.landmarks.filter((landmark) => {
    const isActive = store.activeCategories.includes(landmark.category)
    const matchesSearch = store.searchQuery === '' ||
      landmark.name.toLowerCase().includes(store.searchQuery.toLowerCase()) ||
      landmark.nameZh.includes(store.searchQuery)
    return isActive && matchesSearch
  })
})

function handleSearch(event: Event) {
  const value = (event.target as HTMLInputElement).value
  searchInput.value = value
  store.setSearchQuery(value)
}

function toggleCategory(category: LandmarkCategory) {
  store.toggleCategory(category)
}

function selectLandmark(landmark: Landmark) {
  store.selectLandmark(landmark)
  emit('focus-landmark', landmark)
}

async function exportPostcard() {
  if (isExporting.value) return
  isExporting.value = true
  try {
    const url = `${BACKEND_URL}/api/v1/export-postcard?location_id=${encodeURIComponent(store.currentLocation)}&room_code=${encodeURIComponent(store.roomCode)}`
    const res = await fetch(url)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(`导出失败: ${err.detail || res.statusText}`)
      return
    }
    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = `Vlog_Memory_${store.currentLocation}.jpg`
    a.click()
    URL.revokeObjectURL(objectUrl)
    alert(`✅ AI 明信片已导出！图片内隐藏了 ${store.currentLocation} 的所有地标数据。`)
  } catch (e) {
    console.error('[Postcard] 导出异常:', e)
    alert('导出失败，请检查网络连接。')
  } finally {
    isExporting.value = false
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function importPostcard(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.includes('jpeg') && !file.type.includes('jpg') && !file.name.toLowerCase().endsWith('.jpg')) {
    alert('请上传通过本应用导出的 JPG 明信片图片。')
    return
  }

  isImporting.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('room_code', store.roomCode)
    // target_location_id 已废弃：后端从 EXIF 原产地自动确定导入目标

    const res = await fetch(`${BACKEND_URL}/api/v1/import-postcard`, {
      method: 'POST',
      body: formData,
    })

    const json = await res.json()
    if (!res.ok) {
      alert(`导入失败: ${json.detail || res.statusText}`)
      return
    }

    const { imported, total, imported_location_id } = json.data

    if (imported_location_id && imported_location_id !== store.currentLocation) {
      // 原产地与当前地图不符 → 告知用户并自动飞行
      alert(`✅ 明信片导入成功！共导入 ${imported}/${total} 个地标。\n\n📍 检测到原产地「${imported_location_id}」与当前地图不同，地图将自动飞行过去...`)
      // changeLocation 内部会自动 flyTo + loadFromCloud
      await store.changeLocation(imported_location_id)
    } else {
      // 就在本地图 → 直接刷新
      alert(`✅ 明信片导入成功！共导入 ${imported}/${total} 个地标到 [${store.currentLocation}]。`)
      await store.loadFromCloud()
    }
  } catch (e) {
    console.error('[Postcard] 导入异常:', e)
    alert('导入失败，请检查网络连接。')
  } finally {
    isImporting.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

// --- Vlog 拼接：提取各节点已有 videoUrl，发送给 stitch-vlog ---
async function generateVlog() {
  const videoUrls = filteredLandmarks.value
    .map(lm => lm.videoUrl)
    .filter((url): url is string => !!url && url.trim() !== '')

  // 如果没有视频片段，且没有历史记录
  if (videoUrls.length === 0 && store.vlogHistory.length === 0) {
      alert('No video clips found. Please generate a 5s clip for each node in the Editor first.')
      return
  } else if (videoUrls.length === 0 && store.vlogHistory.length > 0) {
      alert('No video clips found to stitch. Please generate a 5s clip for each node in the Editor first.')
      return
  }

  isGenerating.value = true
  try {
    // 收集有视频的地标的 URL + blob名称 + 地标名（保序对齐）
    const clipsWithMeta = filteredLandmarks.value
      .filter(lm => !!lm.videoUrl && lm.videoUrl.trim() !== '')
      .map(lm => ({
        url: lm.videoUrl as string,
        blobName: (lm.videoBlobName || '') as string,
        name: lm.name || lm.nameZh || ''
      }))

    const submitRes = await fetch(`${BACKEND_URL}/api/v1/stitch-vlog`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_urls: clipsWithMeta.map(c => c.url),
        video_blob_names: clipsWithMeta.map(c => c.blobName),  // 后端用于重新签名
        landmark_names: clipsWithMeta.map(c => c.name),
        room_code: store.roomCode,
        location_id: store.currentLocation,
      })
    })
    const submitData = await submitRes.json()
    if (!submitRes.ok || submitData.code !== 0) {
      alert(`Failed to submit vlog task: ${submitData.detail || submitData.message || 'Unknown error'}`)
      return
    }

    const taskId = submitData.data?.task_id
    if (!taskId) {
      alert('No task_id returned from server for stitching')
      return
    }

    // 轮询拼接状态
    let attempts = 0
    const maxAttempts = 120
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, 2000))
      
      const statusRes = await fetch(`${BACKEND_URL}/task/${taskId}/status`)
      const statusData = await statusRes.json()
      
      if (statusData.code !== 0) {
        alert(`Failed to check stitching status: ${statusData.message}`)
        return
      }

      const status = statusData.data?.status
      if (status === 'completed') {
        await store.loadVlogFromCloud() // Reload history from backend
        return
      } else if (status === 'failed') {
        alert(`Vlog generation failed: ${statusData.data.error || 'Unknown error'}`)
        return
      }
      attempts++
    }
    
    alert('Vlog stitching timed out.')
  } catch (e) {
    alert(`Request failed: ${e}`)
  } finally {
    isGenerating.value = false
  }
}

// --- Vlog 剧本生成：调用 Gemini 2.5 接口 ---
async function generateVlogScript() {
  const activeLandmark = store.selectedLandmark
  if (!activeLandmark) {
    alert('Please select a landmark on the map first / 请先在地图上选择一个地标')
    return
  }

  const landmarks = [activeLandmark.name]

  isGeneratingScript.value = true
  vlogScript.value = []

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/generate-vlog-script`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        landmarks,
        theme: 'Cinematic',
        location_name: store.currentLocation,  // 地理上下文强绑定
      })
    })
    const json = await res.json()
    if (res.ok && json.data && json.data.nodes) {
      vlogScript.value = json.data.nodes
      // 遍历更新地标，注入 AI 字段
      json.data.nodes.forEach((node: any) => {
        const target = store.landmarks.find(l => l.name === node.landmark_name || l.nameZh === node.landmark_name)
        if (target) {
          store.updateLandmarkPreserveCoords(target.id, {
            aiNarrationZh: node.narration_zh,
            aiNarrationEn: node.narration_en,
            aiVideoPrompt: node.video_prompt,
            userVideoPrompt: node.video_prompt,
            openingHours: node.opening_hours,
            coordinates: node.coordinates,
            features: node.features
          })
        }
      })
    } else {
      const errMsg = json.detail || json.message || 'Unknown error'
      console.error('[GenerateScript] Backend error:', json)
      alert(`Script generation failed: ${errMsg}`)
    }
  } catch (e) {
    console.error('[GenerateScript] Fetch failed:', e)
    alert(`Request failed — check console for details.\n${e}`)
  } finally {
    isGeneratingScript.value = false
  }
}

// --- 已废弃：保存 Vlog 到 InsForge 的逻辑已被移除，现在由后端直接写入 Firestore 集合 ---

// --- 下载 Vlog 视频 ---
function downloadVlog(url: string, title: string = 'my_uss_vlog') {
  if (!url) return
  
  // 使用后端代理下载接口，强制触发浏览器下载
  const downloadUrl = `${BACKEND_URL}/api/v1/download-vlog?video_url=${encodeURIComponent(url)}&filename=${encodeURIComponent(title)}.mp4`
  window.location.href = downloadUrl
}

// 格式化时长
function formatDuration(seconds?: number): string {
  if (!seconds) return '0:00'
  const ms = Math.floor(seconds / 60)
  const ss = Math.floor(seconds % 60)
  return `${ms}:${ss.toString().padStart(2, '0')}`
}
</script>

<template>
  <div 
    class="absolute top-0 left-0 bottom-0 z-[1000] flex flex-col transition-transform duration-300 ease-in-out flex-shrink-0"
    :class="isCollapsed ? '-translate-x-full' : 'translate-x-0'"
    style="width: 28rem;"
  >
    <button
      @click="$emit('toggle')"
      class="absolute -right-10 top-1/2 -translate-y-1/2 z-[1001] bg-slate-800/80 backdrop-blur-md shadow-lg rounded-r-lg p-2 hover:bg-slate-700/80 transition-all duration-300 focus:ring-2 focus:ring-slate-400 focus:outline-none"
      aria-label="Toggle sidebar"
    >
      <ChevronLeft v-if="!isCollapsed" class="w-4 h-4 text-slate-200" />
      <ChevronRight v-else class="w-4 h-4 text-slate-200" />
    </button>
    
    <div class="m-4 mr-0 h-full bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden flex flex-col">
      <div class="p-5 border-b border-slate-700/50">
        <h1 class="text-xl font-bold text-white flex items-center gap-2">
          <Rocket class="w-6 h-6 text-orange-500" />
          Nexus Vlog Memory
        </h1>
        <p class="text-sm text-gray-400 mt-1">
          Create your unique vlog at
          <span class="font-semibold text-white capitalize">{{ store.currentLocation || 'anywhere in the world' }}</span>
        </p>
      </div>

      <!-- [Multi-location] 景点切换 - 支持自由输入 -->
      <div class="p-4 border-b border-slate-700/50 bg-slate-800/30">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <MapPin class="w-3.5 h-3.5 text-sky-400" />
            Go to Location
          </span>
          <span class="text-[10px] text-sky-400/70 italic">Tap Enter to fly ✈</span>
        </div>
        <input
          v-model="locationInput"
          list="location-presets"
          type="text"
          placeholder="Type any place in the world..."
          @keydown.enter.prevent="handleLocationSubmit"
          class="w-full px-3 py-1.5 bg-slate-900 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 placeholder-slate-500 transition-all"
        />
        <datalist id="location-presets">
          <option v-for="(cfg, key) in LOCATION_CONFIG" :key="key" :value="key">
            {{ cfg.label }}
          </option>
        </datalist>
      </div>

      <!-- [新增] 数据沙盒体验码控制区 -->
      <div class="p-4 border-b border-slate-700/50 bg-slate-800/40">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Data Sandbox</span>
          <span class="text-xs font-medium text-orange-400 bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 rounded-md">
            Workspace: {{ store.roomCode }}
          </span>
        </div>
        <div class="flex gap-2">
          <input
            v-model="newRoomCode"
            type="text"
            placeholder="Enter Room Code"
            @keydown.enter="switchRoom"
            class="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 placeholder-slate-500 transition-all"
          />
          <button
            @click="switchRoom"
            class="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors border border-slate-600"
          >
            Switch
          </button>
        </div>
      </div>
      
      <div class="p-4 border-b border-slate-700/50">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            :value="searchInput"
            @input="handleSearch"
            placeholder="Filter places in current map..."
            class="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 text-sm focus:outline-none focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 transition-all"
          />
        </div>
      </div>
      
      <div class="p-4 border-b border-slate-700/50">
        <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Categories</h3>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="cat in categories"
            :key="cat"
            @click="store.toggleCategory(cat)"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            :class="store.isCategoryActive(cat) 
              ? `${CATEGORY_INFO[cat].bgColor} text-white` 
              : 'bg-slate-800/40 text-slate-500 opacity-50 saturate-50 hover:bg-slate-700/50'"
          >
            <component :is="iconMap[cat]" class="w-4 h-4" />
            {{ CATEGORY_INFO[cat].name }}
          </button>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto p-4 min-h-0">
        <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          {{ filteredLandmarks.length }} Places
        </h3>
        <div class="space-y-2">
          <button
            v-for="landmark in filteredLandmarks"
            :key="landmark.id"
            @click="selectLandmark(landmark)"
            class="w-full p-3 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 hover:border-slate-600/50 transition-all text-left group"
            :class="{ 'border-orange-500/50 bg-orange-500/10': store.selectedLandmark?.id === landmark.id }"
          >
            <div class="flex items-start gap-3">
              <div 
                class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                :style="{ backgroundColor: CATEGORY_INFO[landmark.category].color }"
              >
                <component :is="iconMap[landmark.category]" class="w-5 h-5 text-white" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-white font-medium text-sm truncate">{{ landmark.name }}</p>
                <p class="text-slate-400 text-xs truncate">{{ landmark.nameZh }}</p>
              </div>
            </div>
          </button>
        </div>
      </div>
      
      <!-- 视频剧本展示区 -->
      <div v-if="vlogScript.length > 0" class="relative p-4 border-t border-slate-700/50 bg-slate-800/30 overflow-y-auto max-h-72">
        <div class="sticky top-0 z-10 flex items-center justify-between mb-3 pb-2 bg-slate-800/90 backdrop-blur -mx-2 px-2 pt-2 rounded-lg">
          <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Sparkles class="w-4 h-4 text-purple-400" />
            AI Generated Script
          </h3>
          <div class="flex items-center gap-2">
            <button @click="isScriptZh = !isScriptZh" class="text-xs bg-slate-700/50 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded transition-colors flex items-center gap-1">
              <Languages class="w-3 h-3" />
              {{ isScriptZh ? 'Switch to EN' : '切换中文' }}
            </button>
            <button @click="vlogScript = []" class="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 px-2 py-1 rounded transition-colors flex items-center gap-1" title="Close Script">
              <X class="w-3 h-3" />
            </button>
          </div>
        </div>
        <div class="space-y-4">
          <div 
            v-for="(node, index) in vlogScript" 
            :key="index"
          >
            <!-- 仅渲染 narration 类型的节点 -->
            <div v-if="node.node_type === 'narration'" class="text-sm rounded-xl p-3 shadow-md border transition-all bg-slate-800/60 border-slate-600/50">
              <div class="flex items-start gap-2.5">
                <span class="mt-0.5 shadow-sm rounded-md bg-slate-700/50 p-1.5 flex-shrink-0">
                  <MessageCircle class="w-3.5 h-3.5 text-blue-400" />
                </span>
                <p class="leading-relaxed flex-1 text-slate-200">
                  <span class="font-bold text-orange-400 block mb-1">[{{ node.landmark_name }}]</span>
                  {{ isScriptZh ? node.narration_zh : node.narration_en }}
                </p>
              </div>
            </div>
            <!-- Video Prompt 节点被隐藏 -->
          </div>
        </div>
      </div>

      <!-- ── 可滚动功能区：AI Script + Stitch + Vlog History ── -->
      <div class="flex-shrink-0 overflow-y-auto border-t border-slate-700/50" style="max-height: 40vh;">
        <!-- AI Script + Stitch + Export/Import 按钮组 -->
        <div class="p-4 space-y-3">
          <button
            @click="generateVlogScript"
            :disabled="isGeneratingScript || filteredLandmarks.length === 0"
            class="w-full flex items-center justify-center gap-2 px-4 py-2 border border-indigo-500/50 bg-indigo-500/10 hover:bg-indigo-500/20 disabled:border-slate-700 disabled:bg-transparent disabled:text-slate-500 text-indigo-300 rounded-xl text-sm font-medium transition-all"
          >
            <Loader2 v-if="isGeneratingScript" class="w-4 h-4 animate-spin" />
            <Sparkles v-else class="w-4 h-4" />
            {{ isGeneratingScript ? 'Generating AI Script...' : 'Generate AI Script' }}
          </button>

          <button
            @click="generateVlog"
            :disabled="isGenerating || filteredLandmarks.length === 0"
            class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg"
          >
            <Loader2 v-if="isGenerating" class="w-4 h-4 animate-spin" />
            <Video v-else class="w-4 h-4" />
            {{ isGenerating ? 'Stitching...' : 'Stitch USS Vlog' }}
          </button>

          <!-- Export / Import 紧随其后 -->
          <div class="flex gap-2">
            <button
              @click="exportPostcard"
              :disabled="isExporting"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-60 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Download class="w-4 h-4" />
              {{ isExporting ? 'Exporting...' : 'Export 📮' }}
            </button>
            <button
              @click="triggerImport"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Upload class="w-4 h-4" />
              Import
            </button>
          </div>
          <input ref="fileInputRef" type="file" accept="image/jpeg,.jpg" class="hidden" @change="importPostcard" />
        </div>

        <!-- Vlog History -->
        <div v-if="store.vlogHistory.length > 0" class="px-4 pb-4 space-y-3 border-t border-slate-700/50 pt-3">
          <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Video class="w-4 h-4 text-pink-400" />
            Vlog History
          </h3>
          <div class="space-y-3">
            <div
              v-for="vlog in store.vlogHistory"
              :key="vlog.vlog_id"
              class="bg-slate-800/80 rounded-xl border border-slate-700/50 shadow-sm overflow-hidden"
            >
              <button @click="openVideoModal(vlog.video_url)" class="w-full relative group block">
                <div class="aspect-video w-full bg-gradient-to-br from-slate-900 via-purple-900/40 to-pink-900/30 flex flex-col items-center justify-center gap-2 transition-all group-hover:from-slate-800 group-hover:via-purple-800/40">
                  <div class="w-12 h-12 rounded-full bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center group-hover:bg-white/20 group-hover:scale-110 transition-all duration-200 shadow-lg">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" class="w-5 h-5 ml-0.5"><path d="M8 5v14l11-7z"/></svg>
                  </div>
                  <span class="text-xs text-white/70 font-medium group-hover:text-white transition-colors">▶ Play in Cinema Mode</span>
                </div>
                <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2.5">
                  <p class="text-xs font-medium text-white truncate">{{ vlog.title || 'Untitled Vlog' }}</p>
                  <p class="text-[10px] text-slate-300" v-if="vlog.clip_count">{{ vlog.clip_count }} clips · {{ formatDuration(vlog.duration) }}</p>
                </div>
              </button>
              <div class="p-2.5">
                <button
                  @click="downloadVlog(vlog.video_url, vlog.title)"
                  class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-medium transition-colors border border-slate-600"
                >
                  <Download class="w-3.5 h-3.5" />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- 影院级全局视频弹窗 (Cinematic Video Modal)                   -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="cinema-fade">
      <div
        v-if="isVideoModalOpen"
        class="fixed inset-0 z-[9000] flex items-center justify-center"
        @click.self="closeVideoModal"
        style="background: rgba(0,0,0,0.92); backdrop-filter: blur(8px);"
      >
        <!-- 关闭按钮 -->
        <button
          @click="closeVideoModal"
          class="absolute top-5 right-6 z-10 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-all hover:scale-110 border border-white/20"
          aria-label="Close video"
        >
          <X class="w-5 h-5" />
        </button>

        <!-- 视频容器 -->
        <div class="relative w-11/12 md:w-4/5 lg:w-3/4 xl:w-2/3 max-w-5xl">
          <!-- 光晕装饰 -->
          <div class="absolute -inset-4 rounded-3xl opacity-30 blur-2xl" style="background: linear-gradient(135deg, #a855f7, #ec4899);"></div>
          <!-- Player -->
          <video
            :src="currentPlayingVideoUrl"
            controls
            autoplay
            class="relative w-full h-auto rounded-2xl shadow-2xl outline-none border border-white/10"
            style="max-height: 82vh;"
          ></video>
          <!-- 标题栏 -->
          <div class="relative mt-3 flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-pink-400 animate-pulse"></div>
            <span class="text-sm text-white/70 font-medium">🎬 Now Playing · Vlog Memory</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

/* 影院弹窗淡入淡出动画 */
.cinema-fade-enter-active,
.cinema-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.cinema-fade-enter-from,
.cinema-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}
</style>
