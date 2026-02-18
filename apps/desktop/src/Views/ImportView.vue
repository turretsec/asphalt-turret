<script lang="ts" setup>
import SDFileBrowser from '../components/imports/SDFileBrowser.vue';
import VolumeSelector from '../components/imports/VolumeSelector.vue';
import JobProgress from '../components/shared/JobProgress.vue';
import { ref, computed } from 'vue';
import type { SDFile, PlayableMedia, ImportFilters, SDCard } from '../api/types';
import Button from 'primevue/button';

const emit = defineEmits<{
  (e: "select", payload: { file: SDFile; volumeUid: string }): void;
  (e: "selection-change", files: SDFile[]): void;
  (e: "import"): void;
  (e: "import-complete"): void;
  (e: "import-dismiss"): void;
  (e: "volume-change", volumeUid: string): void;
  (e: "scan-cards"): void;
}>();

const props = defineProps<{
  sdFileFilters: ImportFilters;
  currentVolumeUid: string;
  currentImportJobId?: number | null;
  availableCards: SDCard[];
  query: string;
}>();


const selectedMedia = ref<PlayableMedia | null>(null);

const selectedId = computed<number | null>(() => 
  selectedMedia.value ? selectedMedia.value.data.id : null
);

const refreshKey = ref(0);

// Expose method to force refresh
defineExpose({
  refresh: () => {
    refreshKey.value++;
  }
});

function onSelectSDFile(payload: { file: SDFile; volumeUid: string }) {
  emit("select", payload);
}

function onSelectionChange(files: SDFile[]) {
  emit("selection-change", files);
}

function onImportComplete() {
  emit("import-complete");
}

function onImportDismiss() {
  emit("import-dismiss");
}

function onVolumeChange(volumeUid: string) {
  emit("volume-change", volumeUid);
}

function onScanCards() {
  emit("scan-cards");
}
</script>

<template>
  <div class="h-full w-full flex flex-col relative">
    <!-- Volume Selector Header (if multiple cards) -->
    <div 
      v-if="availableCards.filter(c => c.is_connected).length > 0"
      class="p-3 border-b border-surface-800"
    >
      <VolumeSelector
        :cards="availableCards"
        :currentVolumeUid="currentVolumeUid"
        @change="onVolumeChange"
      />

      <!-- Scan button -->
      <Button
        label="Scan SD Cards"
        icon="pi pi-refresh"
        @click="onScanCards"
        severity="secondary"
        size="small"
      />
    </div>
    <!-- Job Progress Indicator (floating, centered over this view) -->
    <div 
      v-if="currentImportJobId"
      class="absolute top-4 left-1/2 -translate-x-1/2 bg-surface-800 border border-surface-700 rounded-lg shadow-xl p-4 min-w-96 z-50"
    >
      <JobProgress
        :jobId="currentImportJobId"
        :showToastOnComplete="true"
        @complete="onImportComplete"
        @failed="onImportComplete"
        @dismiss="onImportDismiss"
      />
    </div>

    <div class="flex-1 overflow-hidden">
      <SDFileBrowser
        :key="currentVolumeUid + refreshKey"
        :selectedId="null"
        :query="query"
        :filters="sdFileFilters"
        @select="onSelectSDFile"
        @selection-change="onSelectionChange"
        @import="emit('import')"
      />
    </div>
  </div>
</template>