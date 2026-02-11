<script setup lang="ts">
import ProgressSpinner from "primevue/progressspinner";
import { computed, ref, watch } from "vue";
import { API_BASE } from "../../api/client";
import type { PlayableMedia } from "../../api/types";

const props = defineProps<{
  media: PlayableMedia | null;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const swapping = ref(false);

// prevent race conditions when swapping sources
let swapToken = 0;


const streamUrl = computed(() => {
  if (!props.media) return "";
  
  if (props.media.type === 'clip') {
    return `${API_BASE}/clips/${props.media.data.id}/stream`;
  } else {
    // SD file streaming
    return `${API_BASE}/sd-files/${props.media.data.id}/stream?volume_uid=${props.media.volume_uid}`;
  }
});

const displayName = computed(() => {
  if (!props.media) return "Select a file";
  
  if (props.media.type === 'clip') {
    return props.media.data.original_filename || 'Untitled';
  } else {
    return props.media.data.rel_path;
  }
});

function waitFor(el: HTMLVideoElement, event: keyof HTMLMediaElementEventMap) {
  return new Promise<void>((resolve) => {
    const handler = () => {
      el.removeEventListener(event, handler as any);
      resolve();
    };
    el.addEventListener(event, handler as any, { once: true });
  });
}

watch(
  () => props.media,
  async (newMedia) => {
    const el = videoRef.value;
    if (!el) return;
    
    const token = ++swapToken;
    
    if (!newMedia) {
      swapping.value = false;
      el.pause();
      el.removeAttribute("src");
      el.load();
      return;
    }
    
    swapping.value = true;
    el.pause();
    el.src = streamUrl.value;
    
    await waitFor(el, "loadeddata");
    
    if (token !== swapToken) return;
    
    swapping.value = false;
    try {
      await el.play();
    } catch {
      // autoplay blocked
    }
  },
  { immediate: true }
);
</script>


<template>
  <div class="h-full flex flex-col w-full">
    <div class="flex flex-col w-full p-3 border-b border-surface-800">
      <div class="font-semibold">Player</div>
      <div class="text-xs opacity-70 mt-1">{{ displayName }}</div>
    </div>
    
    <div class="flex-1 p-3">
      <div class="relative w-full h-full rounded-xl bg-black overflow-hidden">
        <video
          ref="videoRef"
          class="w-full h-full bg-black"
          controls
          preload="metadata"
          v-show="media"
        />
        
        <div
          v-show="media && swapping"
          class="absolute inset-0 bg-black/40 backdrop-blur-[1px] flex items-center justify-center"
        >
          <ProgressSpinner style="width: 48px; height: 48px" strokeWidth="4" />
        </div>
        
        <div v-show="!media" class="h-full flex items-center justify-center opacity-70">
          Click a file to play it.
        </div>
      </div>
    </div>
  </div>
</template>
