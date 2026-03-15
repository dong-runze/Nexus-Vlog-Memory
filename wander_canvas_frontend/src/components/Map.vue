<script setup lang="ts">
import { ref, computed, watch, nextTick, shallowRef, markRaw, onMounted } from 'vue'
import { LMap, LTileLayer, LMarker, LIcon } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { store } from '../stores/landmarkStore'
import type { Landmark } from '../types/landmark'
import { CATEGORY_INFO } from '../types/landmark'
import DetailPanel from './DetailPanel.vue'
import EditorModal from './EditorModal.vue'
import Sidebar from './Sidebar.vue'

const emit = defineEmits<{
  (e: 'markerClick', landmark: Landmark): void
}>()

const zoom = ref(17)
const center = ref<[number, number]>([1.2540, 103.8238])

// USS 地图边界，使用 pad(0.1) 增加 10% 缓冲带，防止放大后拖动受限
const bounds = L.latLngBounds(
  [1.2515, 103.8210],
  [1.2565, 103.8255]
).pad(0.1)

const mapRef = shallowRef<InstanceType<typeof LMap> | null>(null)
const isSidebarCollapsed = ref(false)
const markerLayerGroup = shallowRef<L.LayerGroup | null>(null)
const markerInstances = new Map<string, L.Marker>()
const landmarkDataCache = new Map<string, Landmark>()
let isMapDragging = false

// 组件挂载时已在 store.ts 尾部初始化数据，无需再拉取
onMounted(async () => {
  // ...
})

const filteredLandmarks = computed(() => {
  return store.landmarks.filter((landmark) => {
    const isActive = store.activeCategories.includes(landmark.category)
    const matchesSearch = store.searchQuery === '' ||
      landmark.name.toLowerCase().includes(store.searchQuery.toLowerCase()) ||
      landmark.nameZh.includes(store.searchQuery)
    return isActive && matchesSearch
  })
})

function handleMarkerClick(landmark: Landmark) {
  store.selectLandmark(landmark)
}

function flyToLandmark(landmark: Landmark) {
  if (mapRef.value) {
    mapRef.value.leafletObject.flyTo([landmark.lat, landmark.lng], 19, {
      animate: true,
      duration: 1.5
    })
  }
}

// ===================== Multi-location: 监听 store.mapTargetConfig 变化 =====================
// 当切换大景点（changeLocation）或点击地标（selectLandmark）时，mapTargetConfig 会被更新，
// 此 watcher 自动调用 Leaflet 原生 flyTo 实现平滑飞行。
watch(
  () => store.mapTargetConfig,
  (cfg) => {
    if (!cfg || !isMapReady) return
    const leaflet = mapRef.value?.leafletObject as L.Map | undefined
    if (!leaflet) return
    leaflet.flyTo(cfg.center, cfg.zoom, { animate: true, duration: 1.5 })
  },
  { deep: true }
)

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

function createMarkerIcon(landmark: Landmark) {
  const categoryInfo = CATEGORY_INFO[landmark.category]
  const isSpecial = landmark.category === 'special'
  
  const html = `
    <div class="marker-container ${isSpecial ? 'marker-pulse' : ''}">
      <div class="marker-icon" style="background-color: ${categoryInfo.color};">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          ${getIconPath(landmark.category)}
        </svg>
      </div>
      ${isSpecial ? '<div class="marker-ring" style="background-color: #ec4899;"></div>' : ''}
    </div>
  `
  
  return L.divIcon({
    html,
    className: 'custom-marker',
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -36]
  })
}

function getIconPath(category: string): string {
  switch (category) {
    case 'landmark':
      // Rocket icon
      return '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path>'
    case 'school':
      // Star icon
      return '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>'
    case 'dining':
      // IceCreamCone icon
      return '<path d="m7 11 4.08 10.35a1 1 0 0 0 1.84 0L17 11"></path><path d="M17 7A5 5 0 0 0 7 7"></path><path d="M17 7a2 2 0 0 1 0 4H7a2 2 0 0 1 0-4"></path>'
    case 'special':
      // Camera icon
      return '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"></path><circle cx="12" cy="13" r="3"></circle>'
    default:
      // Rocket icon (default)
      return '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path>'
  }
}

function createMarker(landmark: Landmark): L.Marker {
  const lat = parseFloat(landmark.lat.toFixed(6))
  const lng = parseFloat(landmark.lng.toFixed(6))
  
  const marker = markRaw(L.marker([lat, lng], {
    icon: createMarkerIcon(landmark),
    draggable: true
  }))
  
  marker.on('click', () => {
    if (isMapDragging) return
    handleMarkerClick(landmark)
  })
  
  marker.on('dragstart', () => {
    mapRef.value?.leafletObject?.dragging?.disable()
  })
  
  marker.on('dragend', (e) => {
    mapRef.value?.leafletObject?.dragging?.enable()
    
    const newLatLng = e.target.getLatLng()
    const newLat = parseFloat(newLatLng.lat.toFixed(6))
    const newLng = parseFloat(newLatLng.lng.toFixed(6))
    
    e.target.setLatLng([newLat, newLng])
    
    store.updateLandmarkSilent(landmark.id, newLat, newLng)
    
    store.selectLandmark(landmark)
  })
  
  marker.on('contextmenu', (e: L.LeafletMouseEvent) => {
    L.DomEvent.preventDefault(e.originalEvent)
    const cloned = store.cloneLandmark(landmark)
    store.selectLandmark(cloned)
  })
  
  return marker
}

function updateMarkerInstance(marker: L.Marker, landmark: Landmark) {
  const newLat = parseFloat(landmark.lat.toFixed(6))
  const newLng = parseFloat(landmark.lng.toFixed(6))
  
  const currentLatLng = marker.getLatLng()
  if (Math.abs(currentLatLng.lat - newLat) > 0.000001 || 
      Math.abs(currentLatLng.lng - newLng) > 0.000001) {
    marker.setLatLng([newLat, newLng])
  }
  
  const cached = landmarkDataCache.get(landmark.id)
  if (!cached || cached.category !== landmark.category) {
    marker.setIcon(createMarkerIcon(landmark))
  }
  
  landmarkDataCache.set(landmark.id, { ...landmark })
}

function mountMarkerToMap(marker: L.Marker) {
  if (markerLayerGroup.value && !markerLayerGroup.value.hasLayer(marker)) {
    markerLayerGroup.value.addLayer(marker)
    marker.setLatLng(marker.getLatLng())
  }
}

function unmountMarkerFromMap(marker: L.Marker) {
  if (markerLayerGroup.value && markerLayerGroup.value.hasLayer(marker)) {
    markerLayerGroup.value.removeLayer(marker)
  }
}

function syncMarkers() {
  if (!mapRef.value || !mapRef.value.leafletObject) return
  if (!markerLayerGroup.value) return
  
  const allLandmarks = store.landmarks
  const filteredIds = new Set(filteredLandmarks.value.map(l => l.id))
  const existingIds = new Set(markerInstances.keys())
  
  const toDelete: string[] = []
  for (const id of existingIds) {
    if (!allLandmarks.find(l => l.id === id)) {
      toDelete.push(id)
    }
  }
  
  for (const id of toDelete) {
    const marker = markerInstances.get(id)
    if (marker) {
      unmountMarkerFromMap(marker)
      markerInstances.delete(id)
      landmarkDataCache.delete(id)
    }
  }
  
  for (const landmark of allLandmarks) {
    const existingMarker = markerInstances.get(landmark.id)
    
    if (existingMarker) {
      updateMarkerInstance(existingMarker, landmark)
      
      if (filteredIds.has(landmark.id)) {
        mountMarkerToMap(existingMarker)
      } else {
        unmountMarkerFromMap(existingMarker)
      }
    } else {
      const newMarker = createMarker(landmark)
      markerInstances.set(landmark.id, newMarker)
      landmarkDataCache.set(landmark.id, { ...landmark })
      
      if (filteredIds.has(landmark.id)) {
        mountMarkerToMap(newMarker)
      }
    }
  }
}

function renderMarkers() {
  if (!mapRef.value || !mapRef.value.leafletObject) return
  
  const leaflet = mapRef.value.leafletObject as L.Map
  
  try {
    if (markerLayerGroup.value) {
      try {
        markerLayerGroup.value.clearLayers()
      } catch (e) {
        console.warn('clearLayers failed, recreating layer group:', e)
      }
      try {
        markerLayerGroup.value.removeFrom(leaflet)
      } catch (e) {
        console.warn('removeFrom failed:', e)
      }
      markerLayerGroup.value = null
    }
    
    markerLayerGroup.value = markRaw(L.layerGroup().addTo(leaflet))
    markerInstances.clear()
    landmarkDataCache.clear()
    
    for (const landmark of filteredLandmarks.value) {
      const marker = createMarker(landmark)
      markerInstances.set(landmark.id, marker)
      landmarkDataCache.set(landmark.id, { ...landmark })
      markerLayerGroup.value!.addLayer(marker)
    }
  } catch (e) {
    console.error('Error rendering markers:', e)
    markerLayerGroup.value = null
  }
}

let isMapReady = false

watch(() => [
  store.landmarks.map(l => l.id).join(','),
  store.landmarks.map(l => `${l.id}:${l.lat},${l.lng},${l.category}`).join('|'),
  store.activeCategories.join(','),
  store.searchQuery
], () => {
  if (!isMapReady) return
  
  syncMarkers()
}, { deep: true })

function onMapReady() {
  isMapReady = true
  renderMarkers()
  
  const leaflet = mapRef.value?.leafletObject as L.Map
  if (leaflet) {
    leaflet.on('movestart', () => {
      isMapDragging = true
    })
    leaflet.on('moveend', () => {
      setTimeout(() => {
        isMapDragging = false
      }, 50)
    })
  }
}

defineExpose({ flyToLandmark, toggleSidebar, isSidebarCollapsed })
</script>

<template>
  <div class="relative w-full h-screen overflow-hidden">
    <Sidebar 
      @focus-landmark="flyToLandmark" 
      :is-collapsed="isSidebarCollapsed"
      @toggle="toggleSidebar"
    />
    
    <LMap
      ref="mapRef"
      v-model:zoom="zoom"
      v-model:center="center"
      :min-zoom="16"
      :max-zoom="22"
      :max-bounds="bounds"
      :max-bounds-viscosity="0.8"
      class="z-0"
      :use-global-leaflet="false"
      @ready="onMapReady"
    >
      <LTileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
        :max-native-zoom="19"
        :max-zoom="22"
      />
    </LMap>
    
    <DetailPanel v-if="store.isDetailPanelOpen" />
    <EditorModal v-if="store.isEditorModalOpen" />
  </div>
</template>

<style>
.leaflet-container {
  width: 100%;
  height: 100%;
  cursor: grab;
}

.leaflet-container:active {
  cursor: grabbing;
}

.leaflet-control-attribution {
  background: rgba(255, 255, 255, 0.8) !important;
  color: #666 !important;
  font-size: 10px;
}

.leaflet-control-attribution a {
  color: #0078A8 !important;
}

.custom-marker {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
}

.custom-marker:hover {
  cursor: move;
}

.custom-marker:active {
  cursor: grabbing;
}

.marker-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  border: 3px solid white;
  z-index: 2;
}

.marker-ring {
  position: absolute;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  animation: pulse 2s infinite;
  z-index: 1;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}
</style>
