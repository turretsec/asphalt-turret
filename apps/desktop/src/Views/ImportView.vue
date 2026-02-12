<script lang="ts" setup>
import SDFileBrowser from '../components/imports/SDFileBrowser.vue';
import JobProgress from '../components/shared/JobProgress.vue';
import { ref, computed } from 'vue';
import type { SDFile, PlayableMedia, ImportFilters } from '../api/types';

const emit = defineEmits<{
  (e: "select", payload: { file: SDFile; volumeUid: string }): void;
  (e: "selection-change", files: SDFile[]): void;
  (e: "import"): void;
  (e: "import-complete"): void;
  (e: "import-dismiss"): void;  // ← NEW
}>();

const props = defineProps<{
  sdFileFilters: ImportFilters;
  currentVolumeUid: string;
  currentImportJobId?: number | null;  // ← NEW
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

function onImportComplete() {
  emit("import-complete");
}

function onImportDismiss() {
  emit("import-dismiss");
}
</script>

<template>
  <div class="h-full w-full relative">
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

    <SDFileBrowser
      :selectedId="null"
      :query="query"
      :filters="sdFileFilters"
      @select="onSelectSDFile"
      @selection-change="onSelectionChange"
      @import="emit('import')"
    />
  </div>
</template>