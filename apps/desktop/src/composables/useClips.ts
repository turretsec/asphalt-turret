import { ref, computed, reactive } from 'vue';
import { listRepoClips, deleteClips } from '../api/clips';
import type { Clip, CameraEnum, ModeEnum, DatePreset } from '../api/types';

export function useClips() {
  // State
  const clips = ref<Clip[]>([]);
  const selectedClips = ref<Clip[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const sortBy = ref<string>('date-desc');

  // Filters
  const filters = reactive({
    modes: [] as ModeEnum[],
    cameras: [] as CameraEnum[],
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

  function inDateWindow(clipDate: Date | null, preset: DatePreset, range: [Date, Date] | null): boolean {
    if (!clipDate) return false;

    const now = new Date();
    const todayStart = startOfDay(now);

    if (preset === "all") return true;

    if (preset === "today") {
      return clipDate >= todayStart && clipDate <= endOfDay(now);
    }

    if (preset === "yesterday") {
      const y = new Date(todayStart);
      y.setDate(y.getDate() - 1);
      return clipDate >= y && clipDate <= endOfDay(y);
    }

    if (preset === "7d") {
      const start = new Date(todayStart);
      start.setDate(start.getDate() - 6);
      return clipDate >= start && clipDate <= endOfDay(now);
    }

    if (preset === "custom" && range) {
      const [from, to] = range;
      return clipDate >= startOfDay(from) && clipDate <= endOfDay(to);
    }

    return true;
  }

  // Computed: filtered clips

  const filteredClips = computed(() => {
    const q = query.value.trim().toLowerCase();
    const modes = filters.modes;
    const cameras = filters.cameras;

    let result = clips.value.filter((c) => {

      if (modes.length > 0 && !modes.includes(c.mode)) {
        return false;
      }

      if (cameras.length > 0 && !cameras.includes(c.camera)) {
        return false;
      }

      const clipDate = c.recorded_at ? new Date(c.recorded_at) : null;
      if (!inDateWindow(clipDate, filters.datePreset, filters.dateRange)) {
        return false;
      }

      return true;
    });

    // Sorting

    result.sort((a, b) => {
      switch (sortBy.value) {
        case 'date-desc':
          return new Date(b.imported_at).getTime() - new Date(a.imported_at).getTime();
        case 'date-asc':
          return new Date(a.imported_at).getTime() - new Date(b.imported_at).getTime();
        case 'name-asc':
          return a.original_filename.localeCompare(b.original_filename);
        case 'name-desc':
          return b.original_filename.localeCompare(a.original_filename);
        default:
          return 0;
      }
    });

    return result;
  });

  // Actions
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

  async function deleteSelected(): Promise<{ deleted_count: number; failed_count: number; message: string }> {
    if (selectedClips.value.length === 0) {
      throw new Error('No clips selected');
    }

    const response = await deleteClips({
      clip_ids: selectedClips.value.map(c => c.id)
    });

    // Clear selection after successful delete
    selectedClips.value = [];
    
    // Reload clips
    await load();

    return response;
  }

  function setSelection(clips: Clip[]) {
    selectedClips.value = clips;
  }

  function clearSelection() {
    selectedClips.value = [];
  }

  // Return public API
  return {
    // State
    clips,
    filteredClips,
    selectedClips,
    loading,
    error,
    filters,
    query,
    sortBy,

    // Actions
    load,
    deleteSelected,
    setSelection,
    clearSelection,
  };
}