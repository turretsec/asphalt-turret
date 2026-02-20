<script setup lang="ts">
import { ref, watch } from 'vue';
import { useQueryClient } from '@tanstack/vue-query';
import { open } from '@tauri-apps/plugin-dialog';

import MultiSelect from 'primevue/multiselect';
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import ConfirmDialog from 'primevue/confirmdialog';
import { useConfirm } from 'primevue/useconfirm';

import FileToolbar from '../components/shared/FileToolbar.vue';
import MediaPlayer from '../components/shared/MediaPlayer.vue';
import Nav from '../components/common/Nav.vue';
import RepoView from './RepoView.vue';
import ImportView from './ImportView.vue';
import SettingsView from './SettingsView.vue';

import type { SDFile, PlayableMedia, Clip } from '../api/types';
import { CameraEnum, SDFileImportState } from '../api/types';
import { exportClips } from '../api/clips';
import { scanSDCards } from '../api/sd_card';

import { useClips, CLIPS_QUERY_KEY } from '../composables/useClips';
import { useSDFiles, SD_CARDS_QUERY_KEY, SD_FILES_QUERY_KEY } from '../composables/useSDFiles';
import { useActiveJobs } from '../composables/useActiveJobs';

// State

const queryClient    = useQueryClient();
const clipsManager   = useClips();
const sdFilesManager = useSDFiles();
const { addJob }     = useActiveJobs();

const selectedMedia      = ref<PlayableMedia | null>(null);
const mode               = ref<'repo' | 'import' | 'settings'>('repo');
const currentImportJobId = ref<number | null>(null);
const importViewRef      = ref<InstanceType<typeof ImportView> | null>(null);

const toast   = useToast();
const confirm = useConfirm();

// Filter

const cameraOptions: { label: string; value: CameraEnum }[] = [
  { label: 'Front',   value: CameraEnum.FRONT   },
  { label: 'Rear',    value: CameraEnum.REAR    },
  { label: 'Unknown', value: CameraEnum.UNKNOWN },
];

const stateOptions: { label: string; value: SDFileImportState }[] = [
  { label: 'New',      value: SDFileImportState.NEW      },
  { label: 'Imported', value: SDFileImportState.IMPORTED },
  { label: 'Pending',  value: SDFileImportState.PENDING  },
  { label: 'Failed',   value: SDFileImportState.FAILED   },
];

// Navigation

function onSelectMode(m: 'repo' | 'import' | 'settings') {
  mode.value = m;
}

function handleGoToImport() {
  mode.value = 'import';
}

// Clear selection + search when switching tabs.
// No data fetching here — TanStack handles freshness automatically.
watch(mode, () => {
  selectedMedia.value = null;
  clipsManager.query.value  = '';
  sdFilesManager.query.value = '';
  clipsManager.clearSelection();
  sdFilesManager.clearSelection();
});

// Media Selection

function onSelectClip(clip: Clip) {
  selectedMedia.value = { type: 'clip', data: clip };
}

function onSelectSDFile(payload: { file: SDFile; volumeUid: string }) {
  selectedMedia.value = { type: 'sd_file', data: payload.file, volume_uid: payload.volumeUid };
}

// Import

async function handleImport() {
  try {
    const response = await sdFilesManager.importSelected();
    currentImportJobId.value = response.job_id;
    addJob(response.job_id);
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Import Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000,
    });
  }
}

function onImportComplete() {
  currentImportJobId.value = null;

  // The job finished — the data on the server has changed.
  // Invalidate both caches so TanStack refetches them.
  // Any component subscribed to these keys updates automatically.
  queryClient.invalidateQueries({ queryKey: CLIPS_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: ['sd-files'] });  // all sd-files queries
}

function onImportDismiss() {
  currentImportJobId.value = null;
  // Job is still running in background — don't reload yet
}

// SD Card Scanning & Volume Changes

async function handleScanSDCards() {
  try {
    await scanSDCards();

    toast.add({
      severity: 'info',
      summary: 'Scanning SD Cards',
      detail: 'Looking for new files...',
      life: 3000,
    });

    // Scan creates a background job. We don't know exactly when it finishes,
    // so invalidate both cards and files — TanStack will refetch after staleTime.
    // For a tighter integration: track the scan job_id and invalidate on completion.
    queryClient.invalidateQueries({ queryKey: SD_CARDS_QUERY_KEY });
    queryClient.invalidateQueries({ queryKey: ['sd-files'] });

  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Scan Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000,
    });
  }
}

async function handleVolumeChange(volumeUid: string) {
  sdFilesManager.switchToCard(volumeUid);
}

// Clip Actions

async function handleDelete() {
  if (clipsManager.selectedClips.value.length === 0) return;

  const count  = clipsManager.selectedClips.value.length;
  const plural = count > 1 ? 's' : '';

  confirm.require({
    message: `Are you sure you want to delete ${count} clip${plural}?`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    rejectClass: 'p-button-secondary p-button-outlined',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const result = await clipsManager.deleteSelected();
        // deleteSelected() already calls invalidateQueries internally
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: result.message,
          life: 3000,
        });
        clipsManager.clearSelection();
      } catch (e) {
        toast.add({
          severity: 'error',
          summary: 'Delete Failed',
          detail: e instanceof Error ? e.message : 'Unknown error',
          life: 5000,
        });
      }
    },
  });
}

async function handleExport() {
  if (clipsManager.selectedClips.value.length === 0) return;

  try {
    const destination = await open({ directory: true });
    if (!destination) return;

    const result = await exportClips({
      clip_ids: clipsManager.selectedClips.value.map(c => c.id),
      destination_dir: destination as string,
    });

    toast.add({
      severity: result.failed_count > 0 ? 'warn' : 'success',
      summary: 'Export Complete',
      detail: result.message,
      life: 3000,
    });
    clipsManager.clearSelection();
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000,
    });
  }
}
</script>

<template>
  <Toast />
  <ConfirmDialog />
  
  <div class="flex flex-row w-full h-screen bg-surface-950">
    <div class="w-56 flex flex-col border-r border-surface-700">
    <aside class="flex flex-col h-full">
      <div class="p-2">
        <Nav @select="onSelectMode" />
      </div>
      
      <!-- Import sidebar (NO MORE IMPORT BUTTON) -->
      <FileToolbar
        v-if="mode === 'import'"
        class="flex-1"
        v-model:query="sdFilesManager.query.value"
        v-model:modes="sdFilesManager.filters.modes"
        v-model:datePreset="sdFilesManager.filters.datePreset"
        v-model:dateRange="sdFilesManager.filters.dateRange"
      >
        <template #filters>
          <MultiSelect
            v-model="sdFilesManager.filters.states"
            :options="stateOptions"
            :showToggleAll="false"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="State"
            class="flex w-full"
            size="small"
            :pt="{
              label: { class: 'flex flex-col gap-1 items-start' },
            }"
          />
        </template>
        
        <!-- Remove the actions slot - action bar handles it now -->
      </FileToolbar>

      <!-- Repo sidebar (NO MORE DELETE/EXPORT BUTTONS) -->
      <FileToolbar
        v-else-if="mode === 'repo'"
        class="flex-1"
        v-model:query="clipsManager.query.value"
        v-model:modes="clipsManager.filters.modes"
        v-model:datePreset="clipsManager.filters.datePreset"
        v-model:dateRange="clipsManager.filters.dateRange"
      >
        <template #filters>
          <MultiSelect
            v-model="clipsManager.filters.cameras"
            :options="cameraOptions"
            :showToggleAll="false"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="Camera"
            class="flex w-full"
            size="small"
            :pt="{
              label: { class: 'flex flex-col gap-1 items-start' },
            }"
          />
        </template>
        
        <!-- Remove the actions slot - action bar handles it now -->
      </FileToolbar>
    </aside>
  </div>

    <Splitter class="flex-1 h-full overflow-hidden bg-surface-950 border-none"
    >
      <SplitterPanel class="flex items-center justify-center">
        <Splitter orientation="vertical" style="height: 100%;"
          :pt="{
            gutter: { class: 'w-1 bg-surface-700' }
          }"
        >
          <SplitterPanel class="flex flex-col items-center justify-center p-2 bg-surface-900">

            <RepoView
              v-if="mode === 'repo'"
              :clips="clipsManager.filteredClips.value"
              :loading="clipsManager.loading.value"
              :error="clipsManager.error.value"
              :query="clipsManager.query.value"
              :selectedClips="clipsManager.selectedClips.value"
              :filters="clipsManager.filters"
              @select="onSelectClip"
              @update:selectedClips="clipsManager.setSelection"
              @delete-selected="handleDelete"
              @export="handleExport"
              @delete="handleDelete"
              @go-to-import="handleGoToImport"
              @load="clipsManager.reload"
            />

            <ImportView
              v-else-if="mode === 'import'"
              :files="sdFilesManager.filteredSDFiles.value"
              :loading="sdFilesManager.loading.value"
              :filesLoading="sdFilesManager.filesLoading.value"
              :error="sdFilesManager.error.value"
              :currentVolumeUid="sdFilesManager.currentVolumeUid.value"
              :availableCards="sdFilesManager.availableCards.value"
              :query="sdFilesManager.query.value"
              :selectedFiles="sdFilesManager.selectedSDFiles.value"
              :currentImportJobId="currentImportJobId"
              @select="onSelectSDFile"
              @update:selectedFiles="sdFilesManager.setSelection"
              @import-complete="onImportComplete"
              @import-dismiss="onImportDismiss"
              @volume-change="handleVolumeChange"
              @scan-cards="handleScanSDCards"
              @import="handleImport"
              @load="sdFilesManager.reloadAll"
              ref="importViewRef"
            />

            <SettingsView v-else />

          </SplitterPanel>
          
          <SplitterPanel class="flex items-center justify-center bg-surface-950 rounded-sm" v-if="mode !== 'settings'">
            <MediaPlayer 
              :media="selectedMedia" 
            />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
    </Splitter>
  </div>
</template>

<style scoped>
/* Target the gutter directly */
:deep(.p-splitter-gutter) {
  width: 0.5px !important;
}
</style>