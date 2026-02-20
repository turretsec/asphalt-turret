<script setup lang="ts">
import MediaBrowser from '../shared/MediaBrowser.vue';
import type { SortOption } from '../shared/MediaBrowser.vue';
import { ref } from 'vue';
import type { SDFile } from '../../api/types';
import { getSDFileThumbnailUrl } from '../../api/thumbnails';
import { useViewMode } from '../../composables/useViewMode';
import { formatFileSize } from '../../utils/format';
import EmptyState from '../shared/EmptyState.vue';
import ThumbnailImage from '../shared/ThumbnailImage.vue';

const props = defineProps<{
  files: SDFile[];
  loading: boolean;
  error: string | null;
  selectedItems?: SDFile[];
  selectedId: number | null;
  currentVolumeUid: string;
  query: string;
}>();

const emit = defineEmits<{
  (e: 'select', payload: { file: SDFile; volumeUid: string }): void;
  (e: 'update:selectedItems', files: SDFile[]): void;
  (e: 'selection-change', files: SDFile[]): void;
  (e: 'load'): void;
  (e: 'import'): void;
}>();

const { viewMode, toggleViewMode } = useViewMode('sd-files-view-mode');
const thumbnailErrors = ref<Set<number>>(new Set());

// Sort options for SD files
const sortOptions: SortOption[] = [
  { label: 'Date (Newest)', value: 'date-desc' },
  { label: 'Date (Oldest)', value: 'date-asc' },
  { label: 'Name (A-Z)', value: 'name-asc' },
  { label: 'Name (Z-A)', value: 'name-desc' },
];

const sortBy = ref('date-desc');

function onThumbnailError(fileId: number) {
  thumbnailErrors.value.add(fileId);
}

function onSelectFile(file: SDFile) {
  emit('select', { file, volumeUid: props.currentVolumeUid });
}
</script>

<template>
  <MediaBrowser
    :items="files"
    :loading="loading"
    :error="error"
    :selectedItems="selectedItems"
    :selectedId="selectedId"
    :viewMode="viewMode"
    :sortOptions="sortOptions"
    :sortBy="sortBy"
    :query="query"
    :actionBarMode="'files'"
    title="Files"
    @select="onSelectFile"
    @update:selectedItems="emit('update:selectedItems', $event)"
    @selection-change="emit('selection-change', $event)"
    @load="emit('load')"
    @toggle-view="toggleViewMode"
    @import="emit('import')"
  >
    <!-- Item slot — changes based on viewMode -->
    <template #item="{ item: file, viewMode }">

      <!-- Table View -->
      <template v-if="viewMode === 'table'">
        <div class="flex-1 min-w-0 grid grid-cols-4 gap-4 items-center">
          <div class="text-sm truncate col-span-2">{{ file.rel_path }}</div>
          <div class="text-xs opacity-70">{{ formatFileSize(file.size_bytes) }}</div>
          <div class="text-xs">
            <span class="px-2 py-1 rounded bg-surface-800">{{ file.import_state }}</span>
          </div>
        </div>
      </template>

      <!-- Compact View -->
      <template v-else-if="viewMode === 'compact'">
        <div class="flex-shrink-0 w-28 h-16 bg-surface-950 rounded overflow-hidden">
          <ThumbnailImage
            :src="getSDFileThumbnailUrl(currentVolumeUid, file.id)"
            :alt="file.rel_path"
            class="w-full h-full object-cover"
          />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm truncate">{{ file.rel_path }}</div>
          <div class="text-xs opacity-70 mt-1 flex gap-3">
            <span>{{ formatFileSize(file.size_bytes) }}</span>
            <span class="px-2 py-0.5 rounded bg-surface-800">{{ file.import_state }}</span>
          </div>
        </div>
      </template>

      <!-- Expanded View -->
      <template v-else>
        <div class="flex-shrink-0 w-48 h-28 bg-surface-950 rounded overflow-hidden">
          <ThumbnailImage
            :src="getSDFileThumbnailUrl(currentVolumeUid, file.id)"
            :alt="file.rel_path"
            class="w-full h-full object-cover"
          />
        </div>
        <div class="flex-1 min-w-0 flex flex-col justify-center">
          <div class="text-base font-medium truncate">{{ file.rel_path }}</div>
          <div class="text-sm opacity-70 mt-2">
            <div class="flex gap-4">
              <span>{{ formatFileSize(file.size_bytes) }}</span>
              <span class="px-2 py-1 rounded bg-surface-800">{{ file.import_state }}</span>
            </div>
          </div>
        </div>
      </template>

    </template>

    <!-- Empty states -->
    <template #empty>
      <EmptyState
        v-if="!currentVolumeUid"
        icon="pi pi-cloud-upload"
        title="No SD card detected"
        description="Insert a dashcam SD card to view and import video files."
        actionLabel="Scan for SD Cards"
        @action="emit('load')"
      />
      <EmptyState
        v-else-if="loading"
        icon="pi pi-spin pi-spinner"
        title="Loading files..."
        description="Reading files from your SD card."
      />
      <EmptyState
        v-else-if="files.length === 0"
        icon="pi pi-inbox"
        title="SD card is empty"
        description="No video files were found on this SD card."
      />
      <EmptyState
        v-else
        icon="pi pi-filter-slash"
        title="No files match your filters"
        description="Try clearing some filters to see more files."
      />
    </template>

  </MediaBrowser>
</template>