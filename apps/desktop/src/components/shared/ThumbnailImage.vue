<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from 'primevue/skeleton'
import { useThumbnail } from '../../composables/useThumbnail'

const props = defineProps<{
  src: string | null | undefined
  alt?: string
  imgClass?: string
}>()

const srcRef = computed(() => props.src)
const { thumbnailSrc, loading, failed, retry } = useThumbnail(srcRef)
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
  <!--
    Click to retry — this is the escape hatch for VirtualScroller instance
    reuse. If a component previously exhausted MAX_RETRIES (failed = true),
    its srcRef won't change when the scroller recycles the instance for the
    same item, so the watch never fires. retry() manually resets state and
    kicks off a fresh load sequence.
  -->
  <div
    v-else
    class="w-full h-full flex items-center justify-center text-surface-600 cursor-pointer hover:text-surface-400 transition-colors"
    title="Click to retry"
    @click.stop="retry"
  >
    <i class="pi pi-video text-2xl"></i>
  </div>
</template>