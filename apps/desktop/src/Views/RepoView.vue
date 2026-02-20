<script lang="ts" setup>
import ClipBrowser from '../components/clips/ClipBrowser.vue';
import type { Clip, CameraEnum, ModeEnum, DatePreset } from '../api/types';

// All data comes from Shell via props — no fetching here.
// Shell owns useClips, passes filteredClips down.
defineProps<{
  clips: Clip[];
  loading: boolean;
  error: string | null;
  query: string;
  selectedClips: Clip[];
  filters: {
    modes:      ModeEnum[];
    cameras:    CameraEnum[];
    datePreset: DatePreset;
    dateRange:  [Date, Date] | null;
  };
}>();

const emit = defineEmits<{
  (e: 'select', clip: Clip): void;
  (e: 'update:selectedClips', clips: Clip[]): void;
  (e: 'selection-change', clips: Clip[]): void;
  (e: 'delete-selected'): void;
  (e: 'export'): void;
  (e: 'delete'): void;
  (e: 'go-to-import'): void;
  (e: 'load'): void;
}>();
</script>

<template>
  <ClipBrowser
    :clips="clips"
    :loading="loading"
    :error="error"
    :selectedId="null"
    :query="query"
    :selectedItems="selectedClips"
    @select="emit('select', $event)"
    @update:selectedItems="emit('update:selectedClips', $event)"
    @selection-change="emit('selection-change', $event)"
    @load="emit('load')"
    @delete-selected="emit('delete-selected')"
    @export="emit('export')"
    @delete="emit('delete')"
    @go-to-import="emit('go-to-import')"
  />
</template>