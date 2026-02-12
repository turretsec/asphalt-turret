<script lang="ts" setup>
import SDFileBrowser from '../components/imports/SDFileBrowser.vue';
import { ref, computed } from 'vue';
import type { SDFile, PlayableMedia, ImportFilters } from '../api/types';

const emit = defineEmits<{
  (e: "select", payload: { file: SDFile; volumeUid: string }): void;
  (e: "selection-change", files: SDFile[]): void;
  (e: "import"): void;
}>();

const props = defineProps<{
  sdFileFilters: ImportFilters;
  currentVolumeUid: string;
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
  <SDFileBrowser
    :selectedId="null"
    :query="query"
    :filters="sdFileFilters"
    @select="onSelectSDFile"
    @selection-change="onSelectionChange"
    @import="emit('import')"
  />
</template>