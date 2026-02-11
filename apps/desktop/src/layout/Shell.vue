<script setup lang="ts">
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
import type { Clip, SDFile, PlayableMedia, ModeEnum, SDFileImportState } from '../api/types';
import RepoView from '../Views/RepoView.vue';
import ImportView from '../Views/ImportView.vue';
import { importSDFiles } from '../api/imports';

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

onMounted(async () => {
  await load();
});
</script>

<template>
  <Toast />
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
      <SDFileToolsSideBar
        v-if="mode === 'import'"
        class="flex-1 mt-4"
        v-model:query="query"
        v-model:modes="sdFileFilters.modes"
        v-model:states="sdFileFilters.states"
        v-model:datePreset="sdFileFilters.datePreset"
        v-model:dateRange="sdFileFilters.dateRange"
        :selectedFiles="selectedSDFiles"
        :volumeUid="currentVolumeUid"
        @import="handleImport"
      />
    </aside>
    

    
    <Splitter class="flex-1 h-full">
      <SplitterPanel class="flex items-center justify-center">
        <Splitter orientation="vertical" style="height: 100%;">
          <SplitterPanel class="flex flex-col items-center justify-center p-2 bg-surface-950">
            
            <RepoView
              v-if="mode === 'repo'"
              @select="onSelectClip"
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