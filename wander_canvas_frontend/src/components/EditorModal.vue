<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { store } from '../stores/landmarkStore'
import type { Landmark, LandmarkCategory } from '../types/landmark'
import { CATEGORY_INFO } from '../types/landmark'
import { X, Rocket, Star, IceCreamCone, Camera, Save, Video, Loader2, Sparkles } from 'lucide-vue-next'

const name = ref('')
const nameZh = ref('')
const category = ref<LandmarkCategory>('landmark')
const imageUrl = ref('')
const videoUrl = ref('')
const openingHours = ref('')
const introduction = ref('')
const introductionZh = ref('')
const userVideoPrompt = ref('')
const userVideoPromptZh = ref('')
const isGeneratingClip = ref(false)
const isUploadingImage = ref(false)
const isValidatingPrompt = ref(false)
const isValidating = ref(false)
const validationError = ref('')
const editLang = ref<'en' | 'zh'>('en')

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const isEditing = computed(() => !!store.editingLandmark?.id?.toString().startsWith('temp-') === false)

const isValid = computed(() => {
  // 只要填了英文名或中文名其中一个即满足最低要求
  return name.value.trim() !== '' || nameZh.value.trim() !== ''
})

const categories: { id: LandmarkCategory; label: string; labelZh: string; icon: any; color: string }[] = [
  { id: 'landmark', label: 'Attraction', labelZh: '游乐设施', icon: Rocket, color: '#f97316' },
  { id: 'school', label: 'Show', labelZh: '表演', icon: Star, color: '#3b82f6' },
  { id: 'dining', label: 'Dining', labelZh: '餐饮', icon: IceCreamCone, color: '#22c55e' },
  { id: 'special', label: 'Photo Spot', labelZh: '拍照点', icon: Camera, color: '#ec4899' }
]

onMounted(() => {
  if (store.editingLandmark) {
    const data = JSON.parse(JSON.stringify(store.editingLandmark))
    name.value = data.name || ''
    nameZh.value = data.nameZh || ''
    category.value = data.category || 'landmark'
    imageUrl.value = data.imageUrl || ''
    videoUrl.value = data.videoUrl || ''
    openingHours.value = data.openingHours || ''
    introduction.value = data.introduction || ''
    introductionZh.value = data.introductionZh || ''
    userVideoPrompt.value = data.userVideoPrompt !== undefined ? data.userVideoPrompt : (data.aiVideoPrompt || '')
    userVideoPromptZh.value = data.userVideoPromptZh || data.introductionZh || ''
  }
  
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

function closeModal() {
  store.closeEditorModal()
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && store.isEditorModalOpen) {
    e.preventDefault()
    closeModal()
  }
}

function normalizeUrl(url: string): string {
  if (!url) return url
  const trimmed = url.trim()
  if (trimmed && !/^https?:\/\//i.test(trimmed)) {
    return 'https://' + trimmed
  }
  return trimmed
}

/**
 * 本地图片上传：将选中的图片文件上传到后端，获取 GCS 公开 URL
 */
async function handleImageUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  isUploadingImage.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('location_id', store.currentLocation || 'unknown')
    formData.append('room_code', store.roomCode || 'master')

    const res = await fetch(`${BACKEND_URL}/api/v1/upload-image`, {
      method: 'POST',
      body: formData,
    })
    const json = await res.json()

    if (!res.ok || json.code !== 0) {
      alert(`图片上传失败: ${json.detail || json.message || 'Unknown error'}`)
      return
    }

    imageUrl.value = json.data?.image_url || ''
    console.log('[Upload] 图片已上传:', imageUrl.value)
  } catch (e) {
    alert(`上传请求失败: ${e}`)
  } finally {
    isUploadingImage.value = false
    // 清空 input 以允许重复上传同名文件
    input.value = ''
  }
}

/**
 * 单节点视频预览生成：提取 userVideoPrompt 作为 prompt，
 * 先经过 AI 安全卫士校验，通过后调用 /api/v1/generate-clip 生成视频。
 */
async function generateSingleClip() {
  // 防连击锁：安全校验或视频生成任意一项进行中，直接拦截重复点击
  if (isGeneratingClip.value || isValidatingPrompt.value) return

  const prompt = editLang.value === 'zh' ? userVideoPromptZh.value.trim() : userVideoPrompt.value.trim()
  const fallbackPrompt = introduction.value.trim() || introductionZh.value.trim() || name.value.trim()
  let finalPrompt = prompt || fallbackPrompt

  if (!finalPrompt) {
    alert(editLang.value === 'zh' ? '请填写生成提示词或名称。' : 'Please provide a prompt or name.')
    return
  }

  // ——— Step 1: 安全卫士校验 ———
  isValidatingPrompt.value = true
  try {
    const guardRes = await fetch(`${BACKEND_URL}/api/v1/validate-video-prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: finalPrompt }),
    })
    const guardData = await guardRes.json()
    const guard = guardData?.data

    if (guard?.status === 'unsafe') {
      const msg = editLang.value === 'zh'
        ? `${guard.message}\n\n建议修改为：\n${guard.suggested_prompt}\n\n点击"确定"使用建议并生成，点击"取消"自己修改。`
        : `Your prompt may be flagged by the video engine.\n\nSuggested safe version:\n${guard.suggested_prompt}\n\nClick OK to use the suggestion, or Cancel to edit yourself.`
      const accepted = confirm(msg)
      if (!accepted) return   // 用户选择自己修改，中断生成
      // 用 AI 建议替换 prompt，并同步更新表单
      finalPrompt = guard.suggested_prompt
      if (editLang.value === 'zh') {
        userVideoPromptZh.value = finalPrompt
      } else {
        userVideoPrompt.value = finalPrompt
      }
    }
  } catch (e) {
    console.warn('[PromptGuard] 安全校验失败，降级直接生成:', e)
    // 校验服务不可用时降级放行，不阻断用户
  } finally {
    isValidatingPrompt.value = false
  }

  // ——— Step 2: 正式视频生成 ———
  isGeneratingClip.value = true
  try {
    const currentId = store.editingLandmark?.id || `user-${Date.now()}`
    const sourceImageUrl = imageUrl.value.trim()

    const res = await fetch(`${BACKEND_URL}/api/v1/generate-clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_prompt: finalPrompt,
        landmark_id: currentId,
        image_url: sourceImageUrl,
        location_id: store.currentLocation,
        room_code: store.roomCode,
      })
    })
    const resData = await res.json()

    if (!res.ok || resData.code !== 0) {
      alert(`视频生成失败: ${resData.detail || resData.message || 'Unknown error'}`)
      return
    }

    const newVideoUrl = resData.data?.videoUrl || ''
    if (newVideoUrl) {
      videoUrl.value = newVideoUrl
      const storeUpdate: Record<string, any> = { videoUrl: newVideoUrl }
      if (resData.data?.updatedFeaturesEn?.length > 0) {
        storeUpdate.featuresEn = resData.data.updatedFeaturesEn
      }
      if (resData.data?.updatedFeaturesZh?.length > 0) {
        storeUpdate.featuresZh = resData.data.updatedFeaturesZh
      }
      if (store.editingLandmark) {
        store.updateLandmarkPreserveCoords(currentId, storeUpdate)
      }
    } else {
      alert('视频生成完成但 URL 为空，请稍后重试。')
    }
  } catch (e) {
    alert(`请求失败: ${e}`)
  } finally {
    isGeneratingClip.value = false
  }
}

async function saveLandmark() {
  if (!isValid.value || !store.editingLandmark) return

  validationError.value = ''
  // 取用户填写的任意一个名称发给仲裁
  const landmarkName = name.value.trim() || nameZh.value.trim()

  // 地理仲裁校验
  isValidating.value = true
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/validate-landmark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        landmark_name: landmarkName,
        location_name: store.currentLocation,
      })
    })
    const json = await res.json()
    const result = json.data

    if (result?.status === 'invalid') {
      // 拦截！显示错误提示，阻止保存
      validationError.value = result.message || '该地标不属于当前地点'
      return
    }

    if (result?.status === 'valid' || result?.status === 'corrected') {
      // 无论 valid 还是 corrected，都用 Gemini 返回的双语标准名覆写表单
      if (result.standard_name_en) name.value = result.standard_name_en
      if (result.standard_name_zh) nameZh.value = result.standard_name_zh
      if (result?.status === 'corrected') {
        alert(`✅ ${result.message || '地标名称已自动更正'} → EN: ${result.standard_name_en} / ZH: ${result.standard_name_zh}`)
      }
    }
  } catch (e) {
    console.warn('[Validate] 校验服务不可用，降级直接保存:', e)
  } finally {
    isValidating.value = false
  }

  const normalizedImage = normalizeUrl(imageUrl.value)

  const landmarkData: Omit<Landmark, 'lat' | 'lng'> = {
    id: isEditing.value ? store.editingLandmark.id : `user-${Date.now()}`,
    name: name.value.trim(),
    nameZh: nameZh.value.trim(),
    category: category.value,
    imageUrl: normalizedImage || undefined,
    videoUrl: videoUrl.value.trim() || undefined,
    openingHours: openingHours.value.trim() || undefined,
    introduction: introduction.value.trim() || undefined,
    introductionZh: introductionZh.value.trim() || undefined,
    userVideoPrompt: userVideoPrompt.value.trim() || undefined,
    userVideoPromptZh: userVideoPromptZh.value.trim() || undefined,
    isUserCreated: true
  }

  if (isEditing.value) {
    store.updateLandmarkPreserveCoords(store.editingLandmark.id, landmarkData)
  } else {
    store.addLandmark({ ...landmarkData, lat: store.editingLandmark.lat, lng: store.editingLandmark.lng })
  }

  // 保存后强制重新拉取云端最新数据，触发详情面板响应式刷新
  store.closeEditorModal()
  await store.loadFromCloud()
}
</script>

<template>
  <Teleport to="body">
    <div v-if="store.isEditorModalOpen" class="fixed inset-0 z-[1500] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeModal"></div>
      
      <div class="relative w-full max-w-lg bg-slate-900/95 backdrop-blur-xl rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden">
        <div class="flex items-center justify-between p-5 border-b border-slate-700/50">
          <div class="flex items-center gap-4">
            <h2 class="text-lg font-bold text-white">
              {{ isEditing ? (editLang === 'zh' ? '编辑地标' : 'Edit Landmark') : (editLang === 'zh' ? '添加新地标' : 'Add New Landmark') }}
            </h2>
            <div class="flex bg-slate-800 rounded-lg p-0.5 border border-slate-700">
              <button @click="editLang = 'en'" :class="editLang === 'en' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-300'" class="px-3 py-1 text-xs rounded-md transition-all">English</button>
              <button @click="editLang = 'zh'" :class="editLang === 'zh' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-300'" class="px-3 py-1 text-xs rounded-md transition-all">中文</button>
            </div>
          </div>
          <button
            @click="closeModal"
            class="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
        
        <div class="p-5 max-h-[70vh] overflow-y-auto space-y-4">
          <div class="w-full">
            <div v-if="editLang === 'en'">
              <label class="block text-sm font-medium text-slate-300 mb-1.5">Name</label>
              <input
                v-model="name"
                type="text"
                placeholder="e.g., Battlestar Galactica"
                class="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 transition-all"
              />
            </div>
            <div v-else>
              <label class="block text-sm font-medium text-slate-300 mb-1.5">名称</label>
              <input
                v-model="nameZh"
                type="text"
                placeholder="例如：太空堡垒卡拉狄加"
                class="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 transition-all"
              />
            </div>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">
              {{ editLang === 'zh' ? '类别' : 'Category' }}
            </label>
            <div class="grid grid-cols-4 gap-2">
              <button
                v-for="cat in categories"
                :key="cat.id"
                @click="category = cat.id"
                class="flex flex-col items-center gap-1 p-3 rounded-xl border transition-all"
                :class="category === cat.id 
                  ? 'border-orange-500 bg-orange-500/10' 
                  : 'border-slate-700 hover:border-slate-600 bg-slate-800/30'"
              >
                <component 
                  :is="cat.icon" 
                  class="w-5 h-5"
                  :style="{ color: category === cat.id ? cat.color : '#94a3b8' }"
                />
                <span 
                  class="text-xs font-medium"
                  :class="category === cat.id ? 'text-white' : 'text-slate-400'"
                >
                  {{ editLang === 'zh' ? cat.labelZh : cat.label }}
                </span>
              </button>
            </div>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">
              {{ editLang === 'zh' ? '地标图片' : 'Landmark Photo' }}
            </label>

            <!-- 图片预览缩略图 -->
            <div v-if="imageUrl" class="mb-2 relative group rounded-xl overflow-hidden border border-slate-600/50" style="height:120px;">
              <img :src="imageUrl" alt="preview" class="w-full h-full object-cover" />
              <button
                @click="imageUrl = ''"
                class="absolute top-1.5 right-1.5 p-1 bg-black/60 hover:bg-red-600/80 rounded-md text-white/80 text-xs transition-all"
                title="移除图片"
              >✕</button>
            </div>

            <!-- 上传按钮区 -->
            <label
              class="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl border border-dashed cursor-pointer transition-all"
              :class="isUploadingImage
                ? 'border-slate-600/30 bg-slate-800/20 text-slate-500 cursor-not-allowed'
                : 'border-orange-500/40 bg-orange-500/5 hover:bg-orange-500/10 text-orange-400 hover:text-orange-300'"
            >
              <Loader2 v-if="isUploadingImage" class="w-4 h-4 animate-spin" />
              <Camera v-else class="w-4 h-4" />
              <span class="text-sm font-medium">
                {{ isUploadingImage
                    ? (editLang === 'zh' ? '上传中...' : 'Uploading...')
                    : (imageUrl
                        ? (editLang === 'zh' ? '更换图片' : 'Change Photo')
                        : (editLang === 'zh' ? '上传本地图片' : 'Upload Photo')) }}
              </span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="hidden"
                :disabled="isUploadingImage"
                @change="handleImageUpload"
              />
            </label>
          </div>

          <!-- AI Video Prompt 区域 - 始终可编辑 -->
          <div class="mb-3 p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-lg">
            <label class="text-xs text-indigo-400 font-medium mb-1.5 flex items-center gap-1.5">
              <Sparkles class="w-3.5 h-3.5"/> {{ editLang === 'zh' ? 'AI 视频提示词' : 'AI Video Prompt' }}
            </label>
            <textarea
              v-if="editLang === 'en'"
              v-model="userVideoPrompt"
              rows="2"
              placeholder="Edit your 5s video prompt here..."
              class="w-full px-3 py-2 bg-slate-900/50 border border-indigo-500/30 rounded text-xs text-indigo-200 leading-relaxed focus:outline-none focus:border-indigo-400/50 focus:bg-slate-900/80 transition-all resize-none"
            ></textarea>
            <textarea
              v-else
              v-model="userVideoPromptZh"
              rows="2"
              placeholder="在此输入中文视频提示词，后台将自动优化并翻译..."
              class="w-full px-3 py-2 bg-slate-900/50 border border-indigo-500/30 rounded text-xs text-indigo-200 leading-relaxed focus:outline-none focus:border-indigo-400/50 focus:bg-slate-900/80 transition-all resize-none"
            ></textarea>
          </div>

          <!-- 视频生成与预览区 -->
          <div class="border border-slate-700/50 rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium text-slate-300">
                {{ editLang === 'zh' ? '5s AI 小视频' : '5s AI Video Clip' }}
              </label>
              <button
                @click="generateSingleClip"
                :disabled="isGeneratingClip || isValidatingPrompt || (!(editLang === 'zh' ? userVideoPromptZh.trim() : userVideoPrompt.trim()) && !name.trim())"
                class="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 text-white rounded-lg text-xs font-medium transition-all"
              >
                <Loader2 v-if="isGeneratingClip" class="w-3.5 h-3.5 animate-spin" />
                <Video v-else class="w-3.5 h-3.5" />
                {{ isGeneratingClip ? (editLang === 'zh' ? '生成中...' : 'Generating...') : (editLang === 'zh' ? '生成短视频' : 'Generate 5s Video') }}
              </button>
            </div>

            <!-- 视频预览 / 占位 -->
            <div v-if="videoUrl" class="rounded-lg overflow-hidden bg-black">
              <video
                :src="videoUrl"
                controls
                class="w-full rounded-lg"
                style="max-height: 180px;"
              >
                Your browser does not support the video tag.
              </video>
            </div>
            <div v-else class="flex items-center justify-center h-28 bg-slate-800/50 rounded-lg border border-dashed border-slate-600/50 p-2 text-center">
              <p class="text-slate-500 text-xs text-balance">
                {{ editLang === 'zh' ? '暂无短片。完善提示词并点击生成。' : 'No video clip yet. Please check your prompt and click Generate.' }}
              </p>
            </div>
          </div>
        </div>
        
        <div class="p-5 border-t border-slate-700/50">
          <!-- 地理仲裁错误提示条 -->
          <div
            v-if="validationError"
            class="mb-3 px-4 py-3 bg-red-500/10 border border-red-500/40 rounded-xl text-red-300 text-sm leading-snug"
          >
            <p class="font-semibold mb-1">🚨 Location Mismatch Detected</p>
            <p>{{ validationError }}</p>
          </div>
          <div class="flex gap-3">
            <button
              @click="closeModal"
              class="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition-colors"
            >
              {{ editLang === 'zh' ? '取消' : 'Cancel' }}
            </button>
            <button
              @click="saveLandmark"
              :disabled="!isValid || isValidating"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Loader2 v-if="isValidating" class="w-4 h-4 animate-spin" />
              <Save v-else class="w-4 h-4" />
              {{ isValidating ? 'Checking...' : (isEditing ? (editLang === 'zh' ? '更新' : 'Update') : (editLang === 'zh' ? '保存' : 'Save')) }}
            </button>
          </div>
        </div>
      </div>
    </div>
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
</style>
