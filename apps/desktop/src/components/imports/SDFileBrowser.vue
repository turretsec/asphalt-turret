<script setup lang="ts">
import MediaBrowser from '../shared/MediaBrowser.vue';
import { ref, computed, onMounted, watch } from 'vue';
import { listSDCardFiles, listSDCards } from '../../api/sd_card';
import type { SDFile, SDCard, DatePreset, ImportFilters } from '../../api/types';
import { parseModeFromPath, parseDateFromFilename } from '../../utils/file_parser';
import { getSDFileThumbnailUrl } from '../../api/thumbnails';
import { useViewMode } from '../../composables/useViewMode';

const props = defineProps<{
  selectedId: number | null;
  query: string;
  filters: ImportFilters;
  filterMode?: string;
  filterDate?: string;
}>();

const emit = defineEmits<{
  (e: "select", payload: { file: SDFile; volumeUid: string }): void;
  (e: "load"): void;
  (e: "selection-change", files: SDFile[]): void;
  (e: "delete-selected"): void;
  (e: "import"): void;
}>();

// State
const sdCards = ref<SDCard[]>([]);
const sdFiles = ref<SDFile[]>([]);
const loading = ref(false);
const filesLoading = ref(false);
const error = ref<string | null>(null);
const currentVolumeUid = ref<string>('');
const thumbnailErrors = ref<Set<number>>(new Set());
const { viewMode, toggleViewMode } = useViewMode('sd-files-view-mode');

// Date filtering helpers
function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function endOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}

function inDateWindow(fileDate: Date | null, preset: DatePreset, range: [Date, Date] | null): boolean {
  if (!fileDate) return false;

  const now = new Date();
  const todayStart = startOfDay(now);

  if (preset === "all") return true;
  if (preset === "today") {
    return fileDate >= todayStart && fileDate <= endOfDay(now);
  }
  if (preset === "yesterday") {
    const y = new Date(todayStart);
    y.setDate(y.getDate() - 1);
    return fileDate >= y && fileDate <= endOfDay(y);
  }
  if (preset === "7d") {
    const start = new Date(todayStart);
    start.setDate(start.getDate() - 6);
    return fileDate >= start && fileDate <= endOfDay(now);
  }
  if (preset === "custom" && range) {
    const [from, to] = range;
    return fileDate >= startOfDay(from) && fileDate <= endOfDay(to);
  }
  return true;
}

// Computed: filtered files
const displayedFiles = computed(() => {
  const q = props.query.trim().toLowerCase();
  const modes = props.filters.modes;
  const states = props.filters.states;

  return sdFiles.value.filter((f) => {
    // Query
    if (q && !f.rel_path.toLowerCase().includes(q)) return false;

    // Mode
    if (modes.length > 0) {
      const m = parseModeFromPath(f.rel_path);
      if (!m || !modes.includes(m)) return false;
    }

    // State
    if (states.length > 0 && !states.includes(f.import_state)) return false;

    // Date
    const fileDate = parseDateFromFilename(f.rel_path);
    if (!inDateWindow(fileDate, props.filters.datePreset, props.filters.dateRange)) return false;

    return true;
  });
});

// File loading
async function loadFilesForCard(volumeUid: string): Promise<void> {
  filesLoading.value = true;
  
  try {
    const files = await listSDCardFiles(volumeUid);
    sdFiles.value = files;
    console.log(`Loaded ${files.length} files from ${volumeUid}`);
  } catch (e) {
    console.error("Failed to load files:", e);
  } finally {
    filesLoading.value = false;
  }
}

async function loadSDCards() {
  if (loading.value) return;
  loading.value = true;
  error.value = null;
  
  try {
    const data = await listSDCards();
    sdCards.value = data;
    
    const connected = data.find(card => card.is_connected);
    if (connected) {
      currentVolumeUid.value = connected.volume_uid;
      await loadFilesForCard(connected.volume_uid);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load';
  } finally {
    loading.value = false;
  }
}

// Handle select (need to wrap with volumeUid)
function onSelectFile(file: SDFile) {
  emit("select", {
    file: file,
    volumeUid: currentVolumeUid.value
  });
}

// Thumbnail error handling
function onThumbnailError(fileId: number) {
  thumbnailErrors.value.add(fileId);
}

// Utility
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

onMounted(async () => {
  await loadSDCards();
});
</script>

<template>
  <MediaBrowser
    :items="displayedFiles"
    :loading="filesLoading"
    :error="error"
    :selectedId="selectedId"
    :viewMode="viewMode"
    :actionBarMode="'files'"
    title="Files"
    @select="onSelectFile"
    @selection-change="emit('selection-change', $event)"
    @load="loadSDCards"
    @toggle-view="toggleViewMode"
    @delete-selected="emit('delete-selected')"
    @import="emit('import')"
  >
    <template #item="{ item: file, viewMode }">
      <!-- Table View (no thumbnail) -->
      <template v-if="viewMode === 'table'">
        <div class="flex-1 min-w-0 grid grid-cols-4 gap-4 items-center">
          <!-- Path -->
          <div class="text-sm truncate col-span-2">{{ file.rel_path }}</div>
          
          <!-- Size -->
          <div class="text-xs opacity-70">
            {{ formatFileSize(file.size_bytes) }}
          </div>
          
          <!-- Status -->
          <div class="text-xs">
            <span class="px-2 py-1 rounded bg-surface-800">
              {{ file.import_state }}
            </span>
          </div>
        </div>
      </template>

      <!-- Compact View -->
      <template v-else-if="viewMode === 'compact'">
        <div class="flex-shrink-0 w-28 h-16 bg-surface-950 rounded overflow-hidden">
          <img
            v-if="!thumbnailErrors.has(file.id)"
            :src="getSDFileThumbnailUrl(currentVolumeUid, file.id)"
            :alt="file.rel_path"
            class="w-full h-full object-cover"
            @error="onThumbnailError(file.id)"
            loading="lazy"
          />
          <div v-else class="w-full h-full flex items-center justify-center text-surface-600">
            <i class="pi pi-video text-2xl"></i>
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="text-sm truncate">{{ file.rel_path }}</div>
          <div class="text-xs opacity-70 mt-1 flex gap-3">
            <span>{{ formatFileSize(file.size_bytes) }}</span>
            <span class="px-2 py-0.5 rounded bg-surface-800 text-xs">
              {{ file.import_state }}
            </span>
          </div>
        </div>
      </template>

      <!-- Expanded View -->
      <template v-else>
        <div class="flex-shrink-0 w-48 h-28 bg-surface-950 rounded overflow-hidden">
          <img
            v-if="!thumbnailErrors.has(file.id)"
            :src="getSDFileThumbnailUrl(currentVolumeUid, file.id)"
            :alt="file.rel_path"
            class="w-full h-full object-cover"
            @error="onThumbnailError(file.id)"
            loading="lazy"
          />
          <div v-else class="w-full h-full flex items-center justify-center text-surface-600">
            <i class="pi pi-video text-3xl"></i>
          </div>
        </div>

        <div class="flex-1 min-w-0 flex flex-col justify-center">
          <div class="text-base font-medium truncate">{{ file.rel_path }}</div>
          <div class="text-sm opacity-70 mt-2 space-y-1">
            <div class="flex gap-4">
              <span>{{ formatFileSize(file.size_bytes) }}</span>
              <span class="px-2 py-1 rounded bg-surface-800">
                {{ file.import_state }}
              </span>
            </div>
          </div>
        </div>
      </template>
    </template>

    <template #empty>
      <!-- Loading state while scanning -->
      <EmptyState
        v-if="loading"
        icon="pi pi-spin pi-spinner"
        title="Scanning for SD cards..."
        description="Checking connected devices for dashcam footage."
      />
      
      <!-- No files match filters -->
      <EmptyState
        v-else-if="currentVolumeUid && sdFiles.length > 0"
        icon="pi pi-filter-slash"
        title="No files match your filters"
        description="Try clearing some filters or adjusting your search to see more files from your SD card."
      />
      
      <!-- SD card is empty -->
      <EmptyState
        v-else-if="currentVolumeUid && sdFiles.length === 0"
        icon="pi pi-inbox"
        title="SD card is empty"
        description="No video files were found on this SD card. Make sure your dashcam has recorded some footage."
      />
      
      <!-- No SD card detected -->
      <EmptyState
        v-else
        icon="pi pi-cloud-upload"
        title="No SD card detected"
        description="Insert a dashcam SD card to view and import video files. Make sure your SD card is properly connected."
        actionLabel="Scan for SD Cards"
        @action="loadSDCards"
      />
    </template>
  </MediaBrowser>
</template>