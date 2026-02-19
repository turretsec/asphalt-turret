<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from 'primevue/skeleton'
import { useThumbnail } from '../../composables/useThumbnail'

const props = defineProps<{
  src: string | null | undefined
  alt?: string
  imgClass?: string  // CSS classes forwarded to the <img> element
}>()

const srcRef = computed(() => props.src)
const { thumbnailSrc, loading, failed } = useThumbnail(srcRef)
</script>

<template>
  <img
    v-if="thumbnailSrc"
    :src="thumbnailSrc"
    :alt="alt"
    :class="imgClass"
  />
  <Skeleton
    v-else-if="loading && !failed"
    class="w-full h-full"
  />
  <div v-else class="w-full h-full flex items-center justify-center text-surface-600">
    <i class="pi pi-video text-2xl"></i>
  </div>
</template>