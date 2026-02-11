<script lang="ts" setup>
import SDFileTools from '../components/SDFileTools.vue';
import SDFileList from '../components/SDFileList.vue';
import { ref, computed } from 'vue';
import type { SDFile, PlayableMedia, ImportFilters } from '../api/types';

const emit = defineEmits<{
  (e: "select", payload: { file: SDFile; volumeUid: string }): void;
  (e: "selection-change", files: SDFile[]): void;  // ← Add this
}>();

const props = defineProps<{
  sdFileFilters: ImportFilters;
  currentVolumeUid: string;  // ← Add this
}>();

const selectedMedia = ref<PlayableMedia | null>(null);
const query = ref("");

const selectedId = computed<number | null>(() => 
  selectedMedia.value ? selectedMedia.value.data.id : null
);

function onSelectSDFile(payload: { file: SDFile; volumeUid: string }) {
  emit("select", payload);
}

function onSelectionChange(files: SDFile[]) {
  emit("selection-change", files);
}
</script>

<template>
  <SDFileTools 
    v-model:query="query"
  />
  <SDFileList
    :selectedId="selectedId"
    :query="query"
    :filters="sdFileFilters"
    @select="onSelectSDFile"
    @selection-change="onSelectionChange"
  />
</template>