<script setup lang="ts">
import FileToolsSidebar from '../components/FileToolsSidebar.vue';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import ClipBrowser from '../components/ClipBrowser.vue';
import Toast from 'primevue/toast'; 
import ClipPlayer from '../components/ClipPlayer.vue';
import { useToast } from 'primevue/usetoast';
import Nav from '../components/Nav.vue';
import SDFileList from '../components/SDFileList.vue';
import SDFileTree from '../components/SDFileTree.vue';
import SDFileToolsSideBar from '../components/SDFileToolsSideBar.vue';
import { ref, computed, onMounted, watch, reactive } from 'vue';
import { listRepoClips } from '../api/clips';
import { listSDCards } from '../api/sd_card';
import type { Clip, SDFile, PlayableMedia, ModeEnum } from '../api/types';
import { SDFileImportState, CameraEnum } from '../api/types';
import RepoView from '../Views/RepoView.vue';
import ImportView from '../Views/ImportView.vue';
import { importSDFiles } from '../api/imports';
import { deleteClips, exportClips } from '../api/clips';
import InputText from 'primevue/inputtext';
import { open } from '@tauri-apps/plugin-dialog';
import ConfirmDialog from 'primevue/confirmdialog';
import { useConfirm } from 'primevue/useconfirm';

const clips = ref<Clip[]>([]);
const selectedMedia = ref<PlayableMedia | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const mode = ref<"repo" | "import">("repo");
const query = ref("");
const toast = useToast();

// SD card state
const currentVolumeUid = ref<string>('');
const filterMode = ref<string | undefined>();
const filterDate = ref<string | undefined>();

const selectedSDFiles = ref<SDFile[]>([]);  // ← Add this

function onSDFileSelectionChange(files: SDFile[]) {
  selectedSDFiles.value = files;
}

const selectedId = computed<number | null>(() => 
  selectedMedia.value ? selectedMedia.value.data.id : null
);

const filteredClips = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return clips.value;
  
  return clips.value.filter((c) =>
    c.original_filename.toLowerCase().includes(q) ||
    c.file_hash.toLowerCase().includes(q)
  );
});

// Filters for repo clips
const repoFilters = reactive({
  modes: [] as ModeEnum[],
  cameras: [] as CameraEnum[],  // ← New!
  datePreset: "all" as "all" | "today" | "yesterday" | "7d" | "custom",
  dateRange: null as [Date, Date] | null,
});

const filteredSDFiles = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return 
})

async function load(): Promise<void> {
  if (loading.value) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    clips.value = await listRepoClips();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

async function loadConnectedSDCard() {
  try {
    const cards = await listSDCards();
    const connected = cards.find(card => card.is_connected);
    
    if (connected) {
      currentVolumeUid.value = connected.volume_uid;
    }
  } catch (e) {
    console.error('Failed to load SD cards:', e);
  }
}

function onSelectMode(m: "repo" | "import") {
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

function onSelectTreeMode(modeValue: string) {
  filterMode.value = modeValue;
  filterDate.value = undefined;
}

function onSelectTreeDate(payload: { mode: string; date: string }) {
  filterMode.value = payload.mode;
  filterDate.value = payload.date;
}

// Add repo state
const selectedClips = ref<Clip[]>([]);  // ← Track selected clips

// Camera filter options
const cameraOptions: { label: string; value: CameraEnum }[] = [
  { label: "Front", value: CameraEnum.FRONT },
  { label: "Rear", value: CameraEnum.REAR },
  { label: "Unknown", value: CameraEnum.UNKNOWN },
];

// Selection handler for clips
function onClipSelectionChange(clips: Clip[]) {
  selectedClips.value = clips;
}

// Computed for repo action buttons
const canDelete = computed(() => selectedClips.value.length > 0);
const canExport = computed(() => selectedClips.value.length > 0);

const deleteButtonLabel = computed(() => {
  const count = selectedClips.value.length;
  return count > 0 ? `Delete ${count} clip${count > 1 ? 's' : ''}` : 'Delete';
});

const exportButtonLabel = computed(() => {
  const count = selectedClips.value.length;
  return count > 0 ? `Export ${count} clip${count > 1 ? 's' : ''}` : 'Export';
});


const repoViewRef = ref<InstanceType<typeof RepoView> | null>(null);
async function handleDelete() {
  if (selectedClips.value.length === 0) return;
  
  const count = selectedClips.value.length;
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
        const response = await deleteClips({
          clip_ids: selectedClips.value.map(c => c.id)
        });
        
        toast.add({
          severity: 'success',
          summary: 'Clips Deleted',
          detail: response.message,
          life: 3000
        });
        
        // Clear selection
        selectedClips.value = [];
        
        // Reload clips through RepoView
        if (repoViewRef.value) {
          await repoViewRef.value.load();
        }
        
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

const exportDirectory = ref<string>('');  // ← Add this for the input

async function handleExport() {
  if (selectedClips.value.length === 0) return;
  
  const count = selectedClips.value.length;
  const plural = count > 1 ? 's' : '';
  
  try {
    console.log('Opening directory picker...');
    
    // Open native directory picker
    const selected = await open({
      directory: true,
      multiple: false,
      title: `Select folder to export ${count} clip${plural}`
    });
    
    console.log('Selected directory:', selected);
    
    // User cancelled
    if (!selected) {
      console.log('User cancelled dialog');
      return;
    }
    
    console.log('Calling export API with:', {
      clip_ids: selectedClips.value.map(c => c.id),
      destination_dir: selected
    });
    
    const response = await exportClips({
      clip_ids: selectedClips.value.map(c => c.id),
      destination_dir: selected as string
    });
    
    console.log('Export response:', response);
    
    toast.add({
      severity: 'success',
      summary: 'Export Complete',
      detail: `${response.exported_count} clips exported to ${response.destination}`,
      life: 5000
    });
    
    // Clear selection
    selectedClips.value = [];
    
  } catch (e) {
    console.error('Export error:', e);  // ← This will show the real error
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000
    });
  }
}

watch(mode, async () => {
  selectedMedia.value = null;
  query.value = "";
  filterMode.value = undefined;
  filterDate.value = undefined;
  
  if (mode.value === 'repo') {
    await load();
  } else if (mode.value === 'import') {
    await loadConnectedSDCard();
  }
}, { immediate: true });

// Filters for SD files
const sdFileFilters = reactive({
  modes: [] as ModeEnum[],
  states: [] as SDFileImportState[],
  datePreset: "all" as "all" | "today" | "yesterday" | "7d" | "custom",
  dateRange: null as [Date, Date] | null,
});

// For import-specific filters
const stateOptions: { label: string; value: SDFileImportState }[] = [
  { label: "New", value: SDFileImportState.NEW },
  { label: "Imported", value: SDFileImportState.IMPORTED },
  { label: "Pending", value: SDFileImportState.PENDING },
  { label: "Failed", value: SDFileImportState.FAILED },
];

const canImport = computed(() => selectedSDFiles.value.length > 0);
const importButtonLabel = computed(() => {
  const count = selectedSDFiles.value.length;
  return count > 0 ? `Import ${count} file${count > 1 ? 's' : ''}` : 'Import';
});

async function handleImport() {
  if (selectedSDFiles.value.length === 0) return;
  
  try {
    const response = await importSDFiles({
      volume_uid: currentVolumeUid.value,
      file_ids: selectedSDFiles.value.map(f => f.id)
    });
    
    toast.add({
      severity: 'success',
      summary: 'Import Started',
      detail: `Job ${response.job_id} created for ${response.total_files} files`,
      life: 3000
    });
    
    // Clear selection
    selectedSDFiles.value = [];
    
    // Reload files to see updated states
    await loadConnectedSDCard();
    
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Import Failed',
      detail: e instanceof Error ? e.message : 'Unknown error',
      life: 5000
    });
  }
}

const confirm = useConfirm();



onMounted(async () => {
  await load();
});
</script>

<template>
  <Toast />
  <ConfirmDialog />
  <div class="flex flex-row w-full h-screen">
    <aside class="w-56 border-r border-surface-800 p-2 flex flex-col">
      <Nav @select="onSelectMode" />
      
      <!-- Show tree only in import mode -->
      <!--
      <SDFileTree
        v-if="mode === 'import' && currentVolumeUid"
        :volumeUid="currentVolumeUid"
        @selectMode="onSelectTreeMode"
        @selectDate="onSelectTreeDate"
        class="flex-1 mt-4"
      />
      -->
      <!-- Import sidebar -->
      <FileToolsSidebar
        v-if="mode === 'import'"
        class="flex-1 mt-4"
        v-model:query="query"
        v-model:modes="sdFileFilters.modes"
        v-model:datePreset="sdFileFilters.datePreset"
        v-model:dateRange="sdFileFilters.dateRange"
      >
        <template #filters>
          <MultiSelect
            v-model="sdFileFilters.states"
            :options="stateOptions"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="State"
            class="flex w-full"
            size="small"
          />
        </template>

        <template #actions>
          <Button
            :label="importButtonLabel"
            :disabled="!canImport"
            @click="handleImport"
            severity="success"
            class="flex w-full mt-2"
            size="small"
          />
        </template>
      </FileToolsSidebar>

      <!-- Repo sidebar -->
      <FileToolsSidebar
        v-else-if="mode === 'repo'"
        class="flex-1 mt-4"
        v-model:query="query"
        v-model:modes="repoFilters.modes"
        v-model:datePreset="repoFilters.datePreset"
        v-model:dateRange="repoFilters.dateRange"
      >
        <!-- Repo-specific filters -->
        <template #filters>
          <MultiSelect
            v-model="repoFilters.cameras"
            :options="cameraOptions"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="Camera"
            class="flex w-full"
            size="small"
          />
        </template>

        <!-- Repo-specific actions -->
        <template #actions>
          <div class="flex flex-col gap-2 w-full mt-2">
            <Button
              :label="exportButtonLabel"
              :disabled="!canExport"
              @click="handleExport"
              severity="info"
              class="w-full"
              size="small"
              icon="pi pi-download"
            />
            <Button
              :label="deleteButtonLabel"
              :disabled="!canDelete"
              @click="handleDelete"
              severity="danger"
              class="w-full"
              size="small"
              icon="pi pi-trash"
            />
          </div>
        </template>
      </FileToolsSidebar>
    </aside>

    <Splitter class="flex-1 h-full">
      <SplitterPanel class="flex items-center justify-center">
        <Splitter orientation="vertical" style="height: 100%;">
          <SplitterPanel class="flex flex-col items-center justify-center p-2 bg-surface-950">
            
            <RepoView
              v-if="mode === 'repo'"
              ref="repoViewRef"
              @select="onSelectClip"
              @selection-change="onClipSelectionChange"
              :filters="repoFilters"
              :query="query"
            />

            <ImportView
              v-else
              @select="onSelectSDFile"
              @selection-change="onSDFileSelectionChange"
              :sdFileFilters="sdFileFilters"
              :currentVolumeUid="currentVolumeUid"
            />
          </SplitterPanel>
          
          <SplitterPanel class="flex items-center justify-center p-2 bg-surface-950">
            <ClipPlayer :media="selectedMedia" />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
    </Splitter>
  </div>
</template>