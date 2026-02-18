import { ref, computed, reactive } from 'vue';
import { listSDCards, listSDCardFiles } from '../api/sd_card';
import { importSDFiles } from '../api/imports';
import type { SDFile, SDCard, ModeEnum, DatePreset } from '../api/types';
import { parseModeFromPath, parseDateFromFilename } from '../utils/file_parser';
import { SDFileImportState } from '../api/types';

export function useSDFiles() {
  // State
  const sdCards = ref<SDCard[]>([]);
  const sdFiles = ref<SDFile[]>([]);
  const selectedSDFiles = ref<SDFile[]>([]);
  const loading = ref(false);
  const filesLoading = ref(false);
  const error = ref<string | null>(null);
  const currentVolumeUid = ref<string>('');

    // Computed: available cards
  const availableCards = computed(() => sdCards.value);
  const connectedCards = computed(() => sdCards.value.filter(c => c.is_connected));
  const hasMultipleCards = computed(() => connectedCards.value.length > 1);

  // Filters
  const filters = reactive({
    modes: [] as ModeEnum[],
    states: [SDFileImportState.NEW, SDFileImportState.PENDING, SDFileImportState.FAILED] as SDFileImportState[],
    datePreset: "all" as DatePreset,
    dateRange: null as [Date, Date] | null,
  });

  const query = ref("");

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
  const filteredSDFiles = computed(() => {
    const q = query.value.trim().toLowerCase();
    const modes = filters.modes;
    const states = filters.states;

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
      if (!inDateWindow(fileDate, filters.datePreset, filters.dateRange)) return false;

      return true;
    });
  });

  // Actions
  async function loadSDCards() {
    if (loading.value) return;
    loading.value = true;
    error.value = null;
    
    try {
      const data = await listSDCards();
      sdCards.value = data;
      
      // Only consider CONNECTED cards
      const connectedCards = data.filter(card => card.is_connected);
      
      // If no current card selected, pick first CONNECTED one
      if (!currentVolumeUid.value) {
        if (connectedCards.length > 0) {
          currentVolumeUid.value = connectedCards[0].volume_uid;
          await loadFilesForCard(connectedCards[0].volume_uid);
        } else {
          // No connected cards - clear everything
          currentVolumeUid.value = '';
          sdFiles.value = [];
        }
      } else {
        // Check if currently selected card is still connected
        const currentCard = data.find(c => c.volume_uid === currentVolumeUid.value);
        
        if (currentCard && currentCard.is_connected) {
          // Reload current card's files
          await loadFilesForCard(currentVolumeUid.value);
        } else {
          // Current card disconnected - switch to first available or clear
          if (connectedCards.length > 0) {
            currentVolumeUid.value = connectedCards[0].volume_uid;
            await loadFilesForCard(connectedCards[0].volume_uid);
          } else {
            currentVolumeUid.value = '';
            sdFiles.value = [];
          }
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load SD cards';
      currentVolumeUid.value = '';
      sdFiles.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function loadFilesForCard(volumeUid: string): Promise<void> {
    filesLoading.value = true;
    
    try {
      const files = await listSDCardFiles(volumeUid);
      sdFiles.value = files;
      console.log(`Loaded ${files.length} files from ${volumeUid}`);
    } catch (e) {
      console.error("Failed to load files:", e);
      sdFiles.value = [];
    } finally {
      filesLoading.value = false;
    }
  }

  // Switch to different card
  async function switchToCard(volumeUid: string) {
    if (volumeUid === currentVolumeUid.value) return;
    
    currentVolumeUid.value = volumeUid;
    clearSelection(); // Clear selection when switching cards
    await loadFilesForCard(volumeUid);
  }

  async function importSelected(): Promise<{ job_id: number; total_files: number; message: string }> {
    if (selectedSDFiles.value.length === 0) {
      throw new Error('No files selected');
    }

    if (!currentVolumeUid.value) {
      throw new Error('No SD card connected');
    }

    const response = await importSDFiles({
      volume_uid: currentVolumeUid.value,
      file_ids: selectedSDFiles.value.map(f => f.id)
    });

    // Clear selection after successful import
    selectedSDFiles.value = [];
    
    // Reload files to see updated states
    await loadSDCards();

    return response;
  }

  function setSelection(files: SDFile[]) {
    selectedSDFiles.value = files;
  }

  function clearSelection() {
    selectedSDFiles.value = [];
  }

  // Return public API
  return {
    // State
    sdCards,
    sdFiles,
    filteredSDFiles,
    selectedSDFiles,
    loading,
    filesLoading,
    error,
    currentVolumeUid,
    filters,
    query,
    availableCards,
    connectedCards,
    hasMultipleCards,

    // Actions
    loadSDCards,
    loadFilesForCard,
    switchToCard,
    importSelected,
    setSelection,
    clearSelection,
  };
}