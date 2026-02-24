<script lang="ts" setup>
import SDFileBrowser from '../components/imports/SDFileBrowser.vue';
import VolumeSelector from '../components/imports/VolumeSelector.vue';
import JobProgress from '../components/shared/JobProgress.vue';
import Button from 'primevue/button';
import { ref, computed } from 'vue';
import type { SDFile, PlayableMedia, SDCard } from '../api/types';

const props = defineProps<{
  // SD file data — owned by useSDFiles in Shell, passed down
  files: SDFile[];
  loading: boolean;
  filesLoading: boolean;
  error: string | null;
  currentVolumeUid: string;
  availableCards: SDCard[];
  query: string;
  selectedFiles: SDFile[];
  sortBy: string;

  // Job tracking
  currentImportJobId?: number | null;
}>();

const emit = defineEmits<{
  (e: 'select', payload: { file: SDFile; volumeUid: string }): void;
  (e: 'update:selectedFiles', files: SDFile[]): void;
  (e: 'selection-change', files: SDFile[]): void;
  (e: 'import'): void;
  (e: 'import-complete'): void;
  (e: 'import-dismiss'): void;
  (e: 'volume-change', volumeUid: string): void;
  (e: 'scan-cards'): void;
  (e: 'load'): void;
  (e: 'sort-change', sortBy: string): void;
}>();

// Used to force re-mount of SDFileBrowser when card changes
const refreshKey = ref(0);
defineExpose({
  refresh: () => { refreshKey.value++; },
});

const selectedMedia = ref<PlayableMedia | null>(null);
const selectedId = computed<number | null>(() =>
  selectedMedia.value ? selectedMedia.value.data.id : null
);

const connectedCards = computed(() => props.availableCards.filter(c => c.is_connected));
</script>

<template>
  <div class="h-full w-full flex flex-col relative">

    <!-- Volume selector + scan button -->
    <div
      v-if="connectedCards.length > 0"
      class="p-3 border-b border-surface-800 flex items-center gap-2"
    >
      <VolumeSelector
        :cards="availableCards"
        :currentVolumeUid="currentVolumeUid"
        @change="emit('volume-change', $event)"
      />
      <Button
        icon="pi pi-play"
        severity="secondary"
        size="small"
        @click="emit('scan-cards')"
      />
    </div>

    <!-- Floating job progress indicator -->
    <div
      v-if="currentImportJobId"
      class="absolute top-4 left-1/2 -translate-x-1/2 bg-surface-800 border border-surface-700 rounded-lg shadow-xl p-4 min-w-96 z-50"
    >
      <JobProgress
        :jobId="currentImportJobId"
        :showToastOnComplete="true"
        @complete="emit('import-complete')"
        @failed="emit('import-complete')"
        @dismiss="emit('import-dismiss')"
      />
    </div>

    <!-- File browser — pure component, all data comes from props -->
    <div class="flex-1 overflow-hidden">
      <SDFileBrowser
        :key="currentVolumeUid + refreshKey"
        :files="files"
        :loading="filesLoading"
        :error="error"
        :selectedId="selectedId"
        :currentVolumeUid="currentVolumeUid"
        :query="query"
        :selectedItems="selectedFiles"
        :sort-by="sortBy"
        @select="emit('select', $event)"
        @update:selectedItems="emit('update:selectedFiles', $event)"
        @selection-change="emit('selection-change', $event)"
        @load="emit('load')"
        @import="emit('import')"
        @sort-change="emit('sort-change', $event)"
      />
    </div>

  </div>
</template>