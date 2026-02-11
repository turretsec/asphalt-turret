<script lang="ts" setup>

import Tools from '../components/Tools.vue';
import ClipBrowser from '../components/ClipBrowser.vue';

import SDFileList from '../components/SDFileList.vue';
import SDFileTree from '../components/SDFileTree.vue';
import { ref, computed, onMounted, watch } from 'vue';
import { listRepoClips } from '../api/clips';
import { listSDCards } from '../api/sd_card';
import type { Clip, SDFile, PlayableMedia } from '../api/types';

const emit = defineEmits<{
  (e: "select", clip: Clip): void;
}>();

const clips = ref<Clip[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedMedia = ref<PlayableMedia | null>(null);


const selectedId = computed<number | null>(() => 
  selectedMedia.value ? selectedMedia.value.data.id : null
);

const query = ref("");

const filteredClips = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return clips.value;
  
  return clips.value.filter((c) =>
    c.original_filename.toLowerCase().includes(q) ||
    c.file_hash.toLowerCase().includes(q)
  );
});

function onSelectClip(clip: Clip) {
    emit("select", clip);
}

async function load(): Promise<void> {
  if (loading.value) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    clips.value = await listRepoClips();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await load();
});
</script>

<template>
    <Tools v-model:query="query" />
    <ClipBrowser
        :clips="filteredClips"
        :loading="loading"
        :error="error"
        :selectedId="selectedId"
        @select="onSelectClip"
        @load="load"
    />
</template>