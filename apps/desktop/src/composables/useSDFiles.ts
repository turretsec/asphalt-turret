import { ref, computed, reactive } from 'vue';
import { useQuery, useQueryClient } from '@tanstack/vue-query';
import { listSDCards, listSDCardFiles } from '../api/sd_card';
import { importSDFiles } from '../api/imports';
import type { SDFile, SDCard, ImportFilters, DatePreset, ModeEnum, SDFileImportState } from '../api/types';
import { parseModeFromPath, parseDateFromFilename } from '../utils/file_parser';
import { inDateWindow } from '../utils/date';

export const SD_CARDS_QUERY_KEY = ['sd-cards'] as const;
export const SD_FILES_QUERY_KEY = (volumeUid: string) => ['sd-files', volumeUid] as const;

export function useSDFiles() {
  const queryClient = useQueryClient();

  // UI State

  const currentVolumeUid = ref<string>('');
  const selectedSDFiles  = ref<SDFile[]>([]);
  const sortBy           = ref('date-desc');

  const filters = reactive<ImportFilters>({
    modes:      [] as ModeEnum[],
    states:     [] as SDFileImportState[],
    datePreset: 'all' as DatePreset,
    dateRange:  null as [Date, Date] | null,
  });

  const query = ref('');

  // SD Cards list

  const sdCardsQuery = useQuery({
    queryKey: SD_CARDS_QUERY_KEY,
    queryFn: listSDCards,
    staleTime: 30_000,
  });

  const sdCards      = computed(() => sdCardsQuery.data.value ?? []);
  const availableCards  = computed(() => sdCards.value);
  const connectedCards  = computed(() => sdCards.value.filter(c => c.is_connected));
  const hasMultipleCards = computed(() => connectedCards.value.length > 1);

  // Auto-select first connected card when cards load or change
  const _autoSelectCard = computed(() => {
    const cards = connectedCards.value;
    if (cards.length === 0) {
      currentVolumeUid.value = '';
      return;
    }
    const currentStillConnected = cards.some(c => c.volume_uid === currentVolumeUid.value);
    if (!currentVolumeUid.value || !currentStillConnected) {
      currentVolumeUid.value = cards[0].volume_uid;
    }
  });
  void _autoSelectCard.value;

  // SD File List

  const sdFilesQuery = useQuery({
    queryKey: computed(() => SD_FILES_QUERY_KEY(currentVolumeUid.value)),
    queryFn: () => listSDCardFiles(currentVolumeUid.value),
    enabled: computed(() => !!currentVolumeUid.value),
    staleTime: 30_000,
  });

  const sdFiles      = computed(() => sdFilesQuery.data.value ?? []);
  const loading      = computed(() => sdCardsQuery.isLoading.value);
  const filesLoading = computed(() => sdFilesQuery.isLoading.value || sdFilesQuery.isFetching.value);
  const error        = computed(() => {
    const e = sdCardsQuery.error.value ?? sdFilesQuery.error.value;
    return e instanceof Error ? e.message : e ? String(e) : null;
  });

  // Files filtered + sorted

  const filteredSDFiles = computed(() => {
    const q      = query.value.trim().toLowerCase();
    const modes  = filters.modes;
    const states = filters.states;

    const filtered = sdFiles.value.filter((f) => {
      if (q && !f.rel_path.toLowerCase().includes(q)) return false;

      if (modes.length > 0) {
        const m = parseModeFromPath(f.rel_path);
        if (!m || !modes.includes(m)) return false;
      }

      if (states.length > 0 && !states.includes(f.import_state)) return false;

      const fileDate = parseDateFromFilename(f.rel_path);
      if (!inDateWindow(fileDate, filters.datePreset, filters.dateRange)) return false;

      return true;
    });

    // Sort
    return [...filtered].sort((a, b) => {
      switch (sortBy.value) {
        case 'date-desc': {
          const da = parseDateFromFilename(a.rel_path)?.getTime() ?? 0;
          const db = parseDateFromFilename(b.rel_path)?.getTime() ?? 0;
          return db - da;
        }
        case 'date-asc': {
          const da = parseDateFromFilename(a.rel_path)?.getTime() ?? 0;
          const db = parseDateFromFilename(b.rel_path)?.getTime() ?? 0;
          return da - db;
        }
        case 'name-asc':  return a.rel_path.localeCompare(b.rel_path);
        case 'name-desc': return b.rel_path.localeCompare(a.rel_path);
        default:          return 0;
      }
    });
  });

  // Actions

  function switchToCard(volumeUid: string) {
    if (volumeUid === currentVolumeUid.value) return;
    currentVolumeUid.value = volumeUid;
    clearSelection();
  }

  function reloadCards() {
    queryClient.invalidateQueries({ queryKey: SD_CARDS_QUERY_KEY });
  }

  function reloadFiles() {
    if (!currentVolumeUid.value) return;
    queryClient.invalidateQueries({ queryKey: SD_FILES_QUERY_KEY(currentVolumeUid.value) });
  }

  function reloadAll() {
    reloadCards();
    reloadFiles();
  }

  async function importSelected() {
    if (selectedSDFiles.value.length === 0) throw new Error('No files selected');
    if (!currentVolumeUid.value)           throw new Error('No SD card selected');

    const response = await importSDFiles({
      volume_uid: currentVolumeUid.value,
      file_ids: selectedSDFiles.value.map(f => f.id),
    });

    selectedSDFiles.value = [];
    return response;
  }

  function setSelection(files: SDFile[]) {
    selectedSDFiles.value = files;
  }

  function clearSelection() {
    selectedSDFiles.value = [];
  }

  return {
    sdCards,
    sdFiles,
    loading,
    filesLoading,
    error,

    filteredSDFiles,
    availableCards,
    connectedCards,
    hasMultipleCards,

    currentVolumeUid,
    selectedSDFiles,
    filters,
    query,
    sortBy,

    switchToCard,
    reloadCards,
    reloadFiles,
    reloadAll,
    importSelected,
    setSelection,
    clearSelection,
  };
}