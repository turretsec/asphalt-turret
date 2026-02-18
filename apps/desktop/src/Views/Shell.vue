<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
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
import { useClips } from '../composables/useClips';
import { useSDFiles } from '../composables/useSDFiles';
import { useActiveJobs } from '../composables/useActiveJobs';
import JobProgress from '../components/shared/JobProgress.vue';
import { scanSDCards } from '../api/sd_card';

const clipsManager = useClips();
const sdFilesManager = useSDFiles();

const selectedMedia = ref<PlayableMedia | null>(null);
const mode = ref<"repo" | "import" | "settings">("repo");
const toast = useToast();
const confirm = useConfirm();

const { addJob, hasActiveJobs } = useActiveJobs();
const currentImportJobId = ref<number | null>(null);

const importViewRef = ref<InstanceType<typeof ImportView> | null>(null);

function onSelectMode(m: "repo" | "import" | "settings") {
  mode.value = m;
}

function onSelectClip(clip: Clip) {
  selectedMedia.value = {
    type: 'clip',
    data: clip
  };
}

function onSelectSDFile(payload: { file: SDFile; volumeUid: string }) {
  selectedMedia.value = {
    type: 'sd_file',
    data: payload.file,
    volume_uid: payload.volumeUid
  };
}

// Camera filter options
const cameraOptions: { label: string; value: CameraEnum }[] = [
  { label: "Front", value: CameraEnum.FRONT },
  { label: "Rear", value: CameraEnum.REAR },
  { label: "Unknown", value: CameraEnum.UNKNOWN },
];

// State filter options
const stateOptions: { label: string; value: SDFileImportState }[] = [
  { label: "New", value: SDFileImportState.NEW },
  { label: "Imported", value: SDFileImportState.IMPORTED },
  { label: "Pending", value: SDFileImportState.PENDING },
  { label: "Failed", value: SDFileImportState.FAILED },
];

// Delete handler
async function handleDelete() {
  if (clipsManager.selectedClips.value.length === 0) return;
  
  const count = clipsManager.selectedClips.value.length;
  const plural = count > 1 ? 's' : '';
  
  confirm.require({
    message: `Are you sure you want to delete ${count} clip${plural}? This cannot be undone.`,
    header: 'Delete Confirmation',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancel',
    acceptLabel: 'Delete',
    rejectClass: 'p-button-secondary',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const response = await clipsManager.deleteSelected();
        
        toast.add({
          severity: 'success',
          summary: 'Clips Deleted',
          detail: response.message,
          life: 3000
        });
        
      } catch (e) {
        toast.add({
          severity: 'error',
          summary: 'Delete Failed',
          detail: e instanceof Error ? e.message : 'Unknown error',
          life: 5000
        });
      }
    }
  });
}

// Export handler
async function handleExport() {
  if (clipsManager.selectedClips.value.length === 0) return;
  
  const count = clipsManager.selectedClips.value.length;
  const plural = count > 1 ? 's' : '';
  
  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title: `Select folder to export ${count} clip${plural}`
    });
    
    if (!selected) return;
    
    const response = await exportClips({
      clip_ids: clipsManager.selectedClips.value.map(c => c.id),
      destination_dir: selected as string
    });
    
    toast.add({
      severity: 'success',
      summary: 'Export Complete',
      detail: `${response.exported_count} clips exported to ${response.destination}`,
      life: 5000
    });
    
    clipsManager.clearSelection();
    
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000
    });
  }
}

// Import handler
async function handleImport() {
  if (sdFilesManager.selectedSDFiles.value.length === 0) return;
  
  try {
    const response = await sdFilesManager.importSelected();
    
    if (response.job_id > 0) {
      // Track this job
      currentImportJobId.value = response.job_id;
      addJob(response.job_id);
    }
    
    toast.add({
      severity: 'info',
      summary: 'Import Started',
      detail: `Importing ${response.total_files} files...`,
      life: 3000,
    });
    
    // Clear selection after starting import
    sdFilesManager.clearSelection();
    
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
  
  // Reload clips
  clipsManager.load();
  
  // Reload SD card data
  sdFilesManager.loadSDCards().then(() => {
    // Force ImportView to refresh after data is loaded
    importViewRef.value?.refresh();
  });
}

function handleGoToImport() {
  mode.value = 'import';
}

function onImportDismiss() {
  currentImportJobId.value = null;
  // Don't reload - just hide the indicator
}

async function handleVolumeChange(volumeUid: string) {
  await sdFilesManager.switchToCard(volumeUid);
}


async function handleScanSDCards() {
  try {
    const response = await scanSDCards();
    
    toast.add({
      severity: 'info',
      summary: 'Scanning SD Cards',
      detail: 'Looking for new files...',
      life: 3000,
    });
    
    // Reload after a delay to show new files
    setTimeout(() => {
      sdFilesManager.loadSDCards();
    }, 2000);
    
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Scan Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000,
    });
  }
}

watch(mode, async () => {
  selectedMedia.value = null;
  clipsManager.query.value = "";
  sdFilesManager.query.value = "";
  clipsManager.clearSelection();
  sdFilesManager.clearSelection();
  
  if (mode.value === 'repo') {
    await clipsManager.load();
  } else if (mode.value === 'import') {
    await sdFilesManager.loadSDCards();
  }
}, { immediate: true });

onMounted(async () => {
  await clipsManager.load();
});
</script>

<template>
  <Toast />
  <ConfirmDialog />
  
  <div class="flex flex-row w-full h-screen">
    <aside class="w-56 border-r border-surface-800 p-2 flex flex-col">
      <Nav @select="onSelectMode" />
      
      <!-- Import sidebar (NO MORE IMPORT BUTTON) -->
      <FileToolbar
        v-if="mode === 'import'"
        class="flex-1 mt-4"
        v-model:query="sdFilesManager.query.value"
        v-model:modes="sdFilesManager.filters.modes"
        v-model:datePreset="sdFilesManager.filters.datePreset"
        v-model:dateRange="sdFilesManager.filters.dateRange"
      >
        <template #filters>
          <MultiSelect
            v-model="sdFilesManager.filters.states"
            :options="stateOptions"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="State"
            class="flex w-full"
            size="small"
          />
        </template>
        
        <!-- Remove the actions slot - action bar handles it now -->
      </FileToolbar>

      <!-- Repo sidebar (NO MORE DELETE/EXPORT BUTTONS) -->
      <FileToolbar
        v-else-if="mode === 'repo'"
        class="flex-1 mt-4"
        v-model:query="clipsManager.query.value"
        v-model:modes="clipsManager.filters.modes"
        v-model:datePreset="clipsManager.filters.datePreset"
        v-model:dateRange="clipsManager.filters.dateRange"
      >
        <template #filters>
          <MultiSelect
            v-model="clipsManager.filters.cameras"
            :options="cameraOptions"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="Camera"
            class="flex w-full"
            size="small"
          />
        </template>
        
        <!-- Remove the actions slot - action bar handles it now -->
      </FileToolbar>
    </aside>

    <Splitter class="flex-1 h-full">
      <SplitterPanel class="flex items-center justify-center">
        <Splitter orientation="vertical" style="height: 100%;">
          <SplitterPanel class="flex flex-col items-center justify-center p-2 bg-surface-950">

            <RepoView
              v-if="mode === 'repo'"
              @select="onSelectClip"
              @selection-change="clipsManager.setSelection"
              @delete-selected="handleDelete"
              @export="handleExport"
              @delete="handleDelete"
              @go-to-import="handleGoToImport"s
              :filters="clipsManager.filters"
              :query="clipsManager.query.value"
            />

            <ImportView
              v-else-if="mode === 'import'"
              @select="onSelectSDFile"
              @selection-change="sdFilesManager.setSelection"
              @import-complete="onImportComplete"
              @import-dismiss="onImportDismiss"
              @volume-change="handleVolumeChange"
              @scan-cards="handleScanSDCards"
              @import="handleImport"
              :sdFileFilters="sdFilesManager.filters"
              :currentVolumeUid="sdFilesManager.currentVolumeUid.value"
              :currentImportJobId="currentImportJobId"
              :availableCards="sdFilesManager.availableCards.value"
              :query="sdFilesManager.query.value"
              ref="importViewRef"
            />

            <SettingsView v-else />

          </SplitterPanel>
          
          <SplitterPanel class="flex items-center justify-center p-2 bg-surface-950" v-if="mode !== 'settings'">
            <MediaPlayer 
              :media="selectedMedia" 
            />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
    </Splitter>
  </div>
</template>