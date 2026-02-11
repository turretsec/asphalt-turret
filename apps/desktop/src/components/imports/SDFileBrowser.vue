<script setup lang="ts">
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import { ref, computed, onMounted, watch } from 'vue';
import { listSDCardFiles, listSDCards } from '../../api/sd_card';
import type { SDFile, SDCard, DatePreset, ImportFilters } from '../../api/types';
import { parseModeFromPath, parseDateFromFilename } from '../../utils/file_parser';
import { getSDFileThumbnailUrl } from '../../api/thumbnails';

const sdCards = ref<SDCard[]>([]);
const sdFiles = ref<SDFile[]>([]);
const selectedSDFiles = ref<SDFile[]>([]);
const previewFile = ref<SDFile | null>(null);
const loading = ref(false);
const filesLoading = ref(false);
const error = ref<string | null>(null);
const currentVolumeUid = ref<string>('');
const thumbnailErrors = ref<Set<number>>(new Set());

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
}>();

function onThumbnailError(fileId: number) {
  thumbnailErrors.value.add(fileId);
}

// Watch for selection changes and emit
watch(selectedSDFiles, (newSelection) => {
  emit("selection-change", newSelection);
}, { deep: true });

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
    start.setDate(start.getDate() - 6); // inclusive window (today + 6 prior)
    return fileDate >= start && fileDate <= endOfDay(now);
  }

  // custom
  if (preset === "custom" && range) {
    const [from, to] = range;
    return fileDate >= startOfDay(from) && fileDate <= endOfDay(to);
  }

  return true;
}

// Click row to preview
function onRowClick(event: any) {
  if (event.originalEvent.target.closest('.p-checkbox')) {
    return;
  }
  
  emit("select", {
    file: event.data,
    volumeUid: currentVolumeUid.value
  });
}

function rowClass(data: SDFile) {
  // Highlight the currently previewed row
  return previewFile.value?.id === data.id ? 'previewed-row' : '';
}

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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// Filter files based on props
const displayedFiles = computed(() => {
  const q = props.query.trim().toLowerCase();
  const modes = props.filters.modes;
  const states = props.filters.states;
  console.log(states)

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
    const fileDate = parseDateFromFilename(f.rel_path); // Date | null
    if (!inDateWindow(fileDate, props.filters.datePreset, props.filters.dateRange)) return false;

    return true;
  });
});

onMounted(async () => {
  await loadSDCards();
});
</script>

<template>
    <div v-if="displayedFiles.length > 0" class="mt-6 h-full w-full flex flex-col min-h-0">
    <h3 class="shrink-0">Files ({{ displayedFiles.length }})</h3>

    <div v-if="filesLoading" class="shrink-0">Loading files...</div>

    <DataTable
        v-else
        size="small"
        :value="displayedFiles"
        class="flex-1 min-h-0 hoverable-table"
        scrollable
        scrollHeight="flex"
        :virtualScrollerOptions="{ itemSize: 44 }"
        stripedRows
        responsiveLayout="scroll"
        v-model:selection="selectedSDFiles"
        dataKey="id"
        @row-click="onRowClick"
        :rowClass="rowClass"
    >
        <Column selectionMode="multiple" style="width: 3em" />
        <!-- Thumbnail Column -->
        <Column header="Preview" style="width: 8em">
          <template #body="{ data }">
            <div class="w-20 h-12 bg-surface-950 rounded overflow-hidden">
              <img
                v-if="!thumbnailErrors.has(data.id)"
                :src="getSDFileThumbnailUrl(currentVolumeUid, data.id)"
                :alt="data.rel_path"
                class="w-full h-full object-cover"
                @error="onThumbnailError(data.id)"
                loading="lazy"
              />
              <div
                v-else
                class="w-full h-full flex items-center justify-center text-surface-600"
              >
                <i class="pi pi-video"></i>
              </div>
            </div>
          </template>
        </Column>
        
        <Column field="rel_path" header="File Path" />
        <Column field="size_bytes" header="Size">
        <template #body="{ data }">
            {{ formatFileSize(data.size_bytes) }}
        </template>
        </Column>
        <Column field="import_state" header="Status" />
    </DataTable>
    </div>
</template>

<style scoped>
/* Add hover effect manually */
.hoverable-table :deep(.p-datatable-tbody > tr) {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.hoverable-table :deep(.p-datatable-tbody > tr:hover) {
  background-color: #f3f4f6;
}

/* Previewed row styling */
.hoverable-table :deep(.p-datatable-tbody > tr.previewed-row) {
  background-color: #dbeafe;
}

.hoverable-table :deep(.p-datatable-tbody > tr.previewed-row:hover) {
  background-color: #bfdbfe;
}

/* Selected rows (with checkbox) */
.hoverable-table :deep(.p-datatable-tbody > tr.p-highlight) {
  background-color: #fef3c7;
}

.hoverable-table :deep(.p-datatable-tbody > tr.p-highlight:hover) {
  background-color: #fde68a;
}

/* If row is both selected AND previewed */
.hoverable-table :deep(.p-datatable-tbody > tr.p-highlight.previewed-row) {
  background-color: #a5f3fc;
}
</style>