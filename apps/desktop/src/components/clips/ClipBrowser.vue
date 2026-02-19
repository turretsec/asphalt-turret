<script setup lang="ts">
import MediaBrowser from '../shared/MediaBrowser.vue';
import type { SortOption } from '../shared/MediaBrowser.vue';
import { ref } from 'vue';
import type { Clip } from '../../api/types';
import { getClipThumbnailUrl } from '../../api/thumbnails';
import { useViewMode } from '../../composables/useViewMode';
import { formatFileSize, formatDuration } from '../../utils/format';
import EmptyState from '../shared/EmptyState.vue';

const props = defineProps<{
  clips: Clip[];
  query: string;
  loading: boolean;
  error: string | null;
  selectedId: number | null;
  filterMode?: string;
  filterDate?: string;
}>();

const emit = defineEmits<{
  (e: "select", clip: Clip): void;
  (e: "selection-change", clips: Clip[]): void;
  (e: "load"): void;
  (e: "delete-selected"): void;
  (e: "sort-change", value: string): void;
  (e: "export"): void;
  (e: "delete"): void;
  (e: "go-to-import"): void;
}>();

const { viewMode, toggleViewMode } = useViewMode('clips-view-mode');
const thumbnailErrors = ref<Set<number>>(new Set());

function onThumbnailError(clipId: number) {
  thumbnailErrors.value.add(clipId);
}

// Sort options for clips
const sortOptions: SortOption[] = [
  { label: 'Date (Newest)', value: 'date-desc' },
  { label: 'Date (Oldest)', value: 'date-asc' },
  { label: 'Name (A-Z)', value: 'name-asc' },
  { label: 'Name (Z-A)', value: 'name-desc' },
];

const sortBy = ref('date-desc');  // Default sort

function onSortChange(value: string) {
  sortBy.value = value;
  emit('sort-change', value);
}
</script>

<template>
  <MediaBrowser
    :items="clips"
    :loading="loading"
    :error="error"
    :selectedId="selectedId"
    :viewMode="viewMode"
    :sortOptions="sortOptions"
    :query="query"
    :sortBy="sortBy"
    :actionBarMode="'clips'"
    title="Clips"
    @select="emit('select', $event)"
    @selection-change="emit('selection-change', $event)"
    @load="emit('load')"
    @toggle-view="toggleViewMode"
    @delete-selected="emit('delete-selected')"
    @sort-change="onSortChange"
    @export="emit('export')"
    @delete="emit('delete')"
  >
    <!-- Custom content for each clip - changes based on viewMode -->
    <template #item="{ item: clip, viewMode }">
      <!-- Table View -->
      <template v-if="viewMode === 'table'">
        <div class="flex-1 min-w-0 grid grid-cols-5 gap-4 items-center">
          <!-- Filename -->
          <div class="text-sm truncate col-span-2">{{ clip.original_filename }}</div>
          
          <!-- Duration -->
          <div class="text-xs opacity-70">
            {{ formatDuration(clip.duration_s) }}
          </div>
          
          <!-- File Size -->
          <div class="text-xs opacity-70">
            {{ formatFileSize(clip.size_bytes) }}
          </div>
          
          <!-- Date -->
          <div class="text-xs opacity-70">
            {{ new Date(clip.imported_at).toLocaleDateString() }}
          </div>
        </div>
      </template>

      <!-- Compact View -->
      <template v-else-if="viewMode === 'compact'">
        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="text-sm truncate">{{ clip.original_filename }}</div>
          <div class="text-xs opacity-70 mt-1 flex gap-2">
            <span>{{ formatDuration(clip.duration_s) }}</span>
            <span>•</span>
            <span>{{ formatFileSize(clip.size_bytes) }}</span>
          </div>
        </div>

        <!-- Thumbnail (small) -->
        <div class="flex-shrink-0 w-28 h-16 bg-surface-950 rounded overflow-hidden">
          <img
            v-if="!thumbnailErrors.has(clip.id)"
            :src="getClipThumbnailUrl(clip.id)"
            :alt="clip.original_filename"
            class="w-full h-full object-cover"
            @error="onThumbnailError(clip.id)"
            loading="lazy"
          />
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-surface-600"
          >
            <i class="pi pi-video text-2xl"></i>
          </div>
        </div>
      </template>

      <!-- Expanded View -->
      <template v-else>
        <!-- Thumbnail (larger, on left) -->
        <div class="flex-shrink-0 w-48 h-28 bg-surface-950 rounded overflow-hidden">
          <img
            v-if="!thumbnailErrors.has(clip.id)"
            :src="getClipThumbnailUrl(clip.id)"
            :alt="clip.original_filename"
            class="w-full h-full object-cover"
            @error="onThumbnailError(clip.id)"
            loading="lazy"
          />
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-surface-600"
          >
            <i class="pi pi-video text-3xl"></i>
          </div>
        </div>

        <!-- Info (more detailed) -->
        <div class="flex-1 min-w-0 flex flex-col justify-center">
          <div class="text-base font-medium truncate">{{ clip.original_filename }}</div>
          <div class="text-sm opacity-70 mt-2 space-y-1">
            <div class="flex gap-4">
              <span>{{ formatDuration(clip.duration_s) }}</span>
              <span>{{ formatFileSize(clip.size_bytes) }}</span>
            </div>
            <div class="flex gap-4">
              <span>{{ clip.camera || 'Unknown' }}</span>
              <span>{{ clip.mode || 'Unknown' }}</span>
            </div>
            <div class="flex gap-4">
              <span>{{ new Date(clip.imported_at).toLocaleDateString() }}</span>
              <span>{{ new Date(clip.imported_at).toLocaleTimeString() }}</span>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- Custom empty state -->
    <template #empty>
      <EmptyState
        icon="pi pi-video"
        title="No clips in your repository"
        description="Import video files from your dashcam SD card to get started. Your clips will appear here once imported."
        actionLabel="Go to Import"
        @action="$emit('go-to-import')"
      />
    </template>
  </MediaBrowser>
</template>