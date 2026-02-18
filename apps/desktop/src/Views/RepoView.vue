<script lang="ts" setup>
import ClipBrowser from '../components/clips/ClipBrowser.vue';
import { ref, computed, onMounted } from 'vue';
import { listRepoClips } from '../api/clips';
import type { Clip, PlayableMedia, CameraEnum, ModeEnum, DatePreset } from '../api/types';

// Props from Shell
const props = defineProps<{
  filters: {
    modes: ModeEnum[];
    cameras: CameraEnum[];
    datePreset: DatePreset;
    dateRange: [Date, Date] | null;
  };
  query: string;
}>();

// Emits
const emit = defineEmits<{
  (e: "select", clip: Clip): void;
  (e: "selection-change", clips: Clip[]): void;
  (e: "delete-selected"): void;
  (e: "export"): void;
  (e: "delete"): void;
  (e: "go-to-import"): void;
}>();

defineExpose({
  load
});

const clips = ref<Clip[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedMedia = ref<PlayableMedia | null>(null);

const selectedId = computed<number | null>(() => 
  selectedMedia.value ? selectedMedia.value.data.id : null
);

// Helper functions for date filtering (same pattern as SDFileBrowser)
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

// Apply all filters
const filteredClips = computed(() => {
  const q = props.query.trim().toLowerCase();
  const modes = props.filters.modes;
  const cameras = props.filters.cameras;

  return clips.value.filter((c) => {
    // Search query
    if (q && !(
      c.original_filename.toLowerCase().includes(q) ||
      c.file_hash.toLowerCase().includes(q)
    )) {
      return false;
    }

    // Mode filter
    if (modes.length > 0 && !modes.includes(c.mode)) {
      return false;
    }

    // Camera filter
    if (cameras.length > 0 && !cameras.includes(c.camera)) {
      return false;
    }

    // Date filter
    const clipDate = c.recorded_at ? new Date(c.recorded_at) : null;
    if (!inDateWindow(clipDate, props.filters.datePreset, props.filters.dateRange)) {
      return false;
    }

    return true;
  });
});

function onSelectClip(clip: Clip) {
  emit("select", clip);
}

function onSelectionChange(clips: Clip[]) {
  emit("selection-change", clips);  // ← Bubble up to Shell
}

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

onMounted(async () => {
  await load();
});

</script>

<template>
  <ClipBrowser
    :clips="clips"
    :loading="loading"
    :error="error"
    :selectedId="null"
    @select="onSelectClip"
    @selection-change="onSelectionChange"
    @load="() => {}"
    @delete-selected="emit('delete-selected')"
    @export="emit('export')"
    @delete="emit('delete')"
    @go-to-import="emit('go-to-import')"
    :query="query"
  />
</template>