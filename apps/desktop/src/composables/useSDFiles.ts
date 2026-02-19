import { ref, computed, reactive } from 'vue';
import { useQuery, useQueryClient } from '@tanstack/vue-query';
import { listSDCards, listSDCardFiles } from '../api/sd_card';
import { importSDFiles } from '../api/imports';
import type { SDFile, SDCard, ImportFilters, DatePreset, ModeEnum, SDFileImportState } from '../api/types';
import { parseModeFromPath, parseDateFromFilename } from '../utils/file_parser';
import { inDateWindow } from '../utils/date';

// Query keys
// Exported so Shell can invalidate these after import/scan completes.

export const SD_CARDS_QUERY_KEY  = ['sd-cards'] as const;
export const SD_FILES_QUERY_KEY  = (volumeUid: string) => ['sd-files', volumeUid] as const;

// Composable

export function useSDFiles() {
  const queryClient = useQueryClient();

  // UI State

  const currentVolumeUid = ref<string>('');
  const selectedSDFiles  = ref<SDFile[]>([]);

  const filters = reactive<ImportFilters>({
    modes:      [] as ModeEnum[],
    states:     [] as SDFileImportState[],
    datePreset: 'all' as DatePreset,
    dateRange:  null as [Date, Date] | null,
  });

  const query = ref('');

  // SD Cards list
  //
  // Fetches once, caches for 30s. Auto-selects the first connected card
  // via the onSuccess side-effect below.

  const sdCardsQuery = useQuery({
    queryKey: SD_CARDS_QUERY_KEY,
    queryFn: listSDCards,
    staleTime: 30_000,
  });

  // When sd-cards data arrives (or updates), auto-select a card if none selected.
  // This replaces the `loadSDCards()` logic that handled initial card selection.
  const sdCards = computed(() => sdCardsQuery.data.value ?? []);

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
    // Only auto-select if nothing is selected yet, or current card disconnected
    const currentStillConnected = cards.some(c => c.volume_uid === currentVolumeUid.value);
    if (!currentVolumeUid.value || !currentStillConnected) {
      currentVolumeUid.value = cards[0].volume_uid;
    }
  });
  // Trigger the computed to run reactively (Vue tracks it)
  void _autoSelectCard.value;

  // SD File List
  //
  // The query key includes currentVolumeUid. When the user switches cards
  // (setting currentVolumeUid.value), TanStack automatically fires a new
  // request for the new card — no switchToCard() logic needed.
  //
  // enabled: skip the fetch until we actually have a card selected.

  const sdFilesQuery = useQuery({
    queryKey: computed(() => SD_FILES_QUERY_KEY(currentVolumeUid.value)),
    queryFn: () => listSDCardFiles(currentVolumeUid.value),
    enabled: computed(() => !!currentVolumeUid.value),
    staleTime: 30_000,
  });

  const sdFiles     = computed(() => sdFilesQuery.data.value ?? []);
  const loading     = computed(() => sdCardsQuery.isLoading.value);
  const filesLoading = computed(() => sdFilesQuery.isLoading.value || sdFilesQuery.isFetching.value);
  const error       = computed(() => {
    const e = sdCardsQuery.error.value ?? sdFilesQuery.error.value;
    return e instanceof Error ? e.message : e ? String(e) : null;
  });

  // Files filtered

  const filteredSDFiles = computed(() => {
    const q      = query.value.trim().toLowerCase();
    const modes  = filters.modes;
    const states = filters.states;

    return sdFiles.value.filter((f) => {
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
  });

  // Actions

  // Switch to a different SD card.
  // Just set the volumeUid — TanStack handles the fetch automatically
  // because the query key is reactive.
  function switchToCard(volumeUid: string) {
    if (volumeUid === currentVolumeUid.value) return;
    currentVolumeUid.value = volumeUid;
    clearSelection();
  }

  // Reload SD cards list (e.g. after a scan job completes).
  function reloadCards() {
    queryClient.invalidateQueries({ queryKey: SD_CARDS_QUERY_KEY });
  }

  // Reload files for the current card (e.g. after import completes).
  function reloadFiles() {
    if (!currentVolumeUid.value) return;
    queryClient.invalidateQueries({ queryKey: SD_FILES_QUERY_KEY(currentVolumeUid.value) });
  }

  // Reload everything (cards + current card's files).
  function reloadAll() {
    reloadCards();
    reloadFiles();
  }

  // Start an import for the currently selected files.
  // Returns the job response so Shell can start tracking it.
  // Invalidation happens in Shell's onImportComplete when the job finishes —
  // NOT here, because the files haven't actually changed yet at this point.
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
    // Server state
    sdCards,
    sdFiles,
    loading,
    filesLoading,
    error,

    // Derived
    filteredSDFiles,
    availableCards,
    connectedCards,
    hasMultipleCards,

    // UI state
    currentVolumeUid,
    selectedSDFiles,
    filters,
    query,

    // Actions
    switchToCard,
    reloadCards,
    reloadFiles,
    reloadAll,
    importSelected,
    setSelection,
    clearSelection,
  };
}