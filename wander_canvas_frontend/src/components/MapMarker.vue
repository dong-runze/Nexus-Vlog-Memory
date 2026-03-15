<script setup lang="ts">
import { computed } from 'vue'
import { LMarker, LIcon } from '@vue-leaflet/vue-leaflet'
import type { Landmark } from '../types/landmark'
import { CATEGORY_INFO } from '../types/landmark'

const props = defineProps<{
  landmark: Landmark
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const categoryInfo = computed(() => CATEGORY_INFO[props.landmark.category])

const iconHtml = computed(() => {
  const isSpecial = props.landmark.category === 'special'
  const bgColor = categoryInfo.value.color
  const pulseClass = isSpecial ? 'marker-pulse' : ''
  
  return `
    <div class="marker-container ${pulseClass}">
      <div class="marker-icon" style="background-color: ${bgColor};">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          ${getIconPath(props.landmark.category)}
        </svg>
      </div>
      ${isSpecial ? '<div class="marker-ring" style="background-color: #ec4899;"></div>' : ''}
    </div>
  `
})

function getIconPath(category: string): string {
  switch (category) {
    case 'landmark':
      return '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle>'
    case 'school':
      return '<path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path>'
    case 'dining':
      return '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"></path><path d="M7 2v20"></path><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path>'
    case 'special':
      return '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path>'
    default:
      return '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle>'
  }
}

import { type PointTuple } from 'leaflet'

const icon = computed(() => ({
  html: iconHtml.value,
  className: 'custom-marker',
  iconSize: [36, 36] as PointTuple,
  iconAnchor: [18, 18] as PointTuple,
  popupAnchor: [0, -18] as PointTuple
}))
</script>

<template>
  <LMarker
    :lat-lng="[landmark.lat, landmark.lng]"
    @click="emit('click')"
  >
    <LIcon v-bind="icon" />
  </LMarker>
</template>

<style>
.custom-marker {
  display: flex;
  align-items: center;
  justify-content: center;
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
