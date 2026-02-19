import { ref, computed, reactive } from 'vue';
import { useQuery, useQueryClient } from '@tanstack/vue-query';
import { listRepoClips, deleteClips } from '../api/clips';
import type { Clip, CameraEnum, ModeEnum, DatePreset } from '../api/types';
import { inDateWindow } from '../utils/date';

// Query Key
// Exported so other composables (e.g. useSDFiles after import) can invalidate it
// without hard-coding the string.
export const CLIPS_QUERY_KEY = ['clips'] as const;

// Composable

export function useClips() {
  const queryClient = useQueryClient();

  // Server State
  //
  // useQuery fires listRepoClips() on first use, caches the result under
  // CLIPS_QUERY_KEY, and shares it across every component that calls useClips().
  // If two components mount at the same time, only ONE network request fires.
  //
  // staleTime: 60s — clips only change after an explicit import or delete,
  // both of which call invalidateQueries to force a fresh fetch.
  //
  const clipsQuery = useQuery({
    queryKey: CLIPS_QUERY_KEY,
    queryFn: listRepoClips,
    staleTime: 60_000,
  });

  // Convenience aliases that match the old composable's public surface,
  // so existing call sites in Shell/RepoView need minimal changes.
  const clips = computed(() => clipsQuery.data.value ?? []);
  const loading = computed(() => clipsQuery.isLoading.value);
  const error = computed(() =>
    clipsQuery.error.value instanceof Error
      ? clipsQuery.error.value.message
      : clipsQuery.error.value
        ? String(clipsQuery.error.value)
        : null
  );

  // UI State
  //
  // These are NOT server state — they live in the user's session and don't
  // need to be cached or synced with the backend.

  const selectedClips = ref<Clip[]>([]);

  const filters = reactive({
    modes:      [] as ModeEnum[],
    cameras:    [] as CameraEnum[],
    datePreset: 'all' as DatePreset,
    dateRange:  null as [Date, Date] | null,
  });

  const query   = ref('');
  const sortBy  = ref('date-desc');

  // Derived State

  const filteredClips = computed(() => {
    const q       = query.value.trim().toLowerCase();
    const modes   = filters.modes;
    const cameras = filters.cameras;

    const result = clips.value.filter((c) => {
      if (q && !(
        c.original_filename?.toLowerCase().includes(q) ||
        c.file_hash.toLowerCase().includes(q)
      )) return false;

      if (modes.length > 0 && !modes.includes(c.mode)) return false;
      if (cameras.length > 0 && !cameras.includes(c.camera)) return false;

      const clipDate = c.recorded_at ? new Date(c.recorded_at) : null;
      if (!inDateWindow(clipDate, filters.datePreset, filters.dateRange)) return false;

      return true;
    });

    result.sort((a, b) => {
      switch (sortBy.value) {
        case 'date-desc': return new Date(b.imported_at).getTime() - new Date(a.imported_at).getTime();
        case 'date-asc':  return new Date(a.imported_at).getTime() - new Date(b.imported_at).getTime();
        case 'name-asc':  return (a.original_filename ?? '').localeCompare(b.original_filename ?? '');
        case 'name-desc': return (b.original_filename ?? '').localeCompare(a.original_filename ?? '');
        default:          return 0;
      }
    });

    return result;
  });

  // Actions

  // Manually trigger a refetch (e.g. the refresh button).
  // Most of the time you won't need this — invalidateQueries handles it.
  function reload() {
    queryClient.invalidateQueries({ queryKey: CLIPS_QUERY_KEY });
  }

  async function deleteSelected(): Promise<{ deleted_count: number; failed_count: number; message: string }> {
    if (selectedClips.value.length === 0) throw new Error('No clips selected');

    const response = await deleteClips({
      clip_ids: selectedClips.value.map(c => c.id),
    });

    selectedClips.value = [];

    // Tell TanStack the clips data is now stale — it refetches automatically
    // for any component currently subscribed to ['clips'].
    queryClient.invalidateQueries({ queryKey: CLIPS_QUERY_KEY });

    return response;
  }

  function setSelection(clips: Clip[]) {
    selectedClips.value = clips;
  }

  function clearSelection() {
    selectedClips.value = [];
  }

  return {
    // Server state (read-only computed — don't assign to these)
    clips,
    loading,
    error,

    // Derived
    filteredClips,

    // UI state
    selectedClips,
    filters,
    query,
    sortBy,

    // Actions
    reload,
    deleteSelected,
    setSelection,
    clearSelection,
  };
}