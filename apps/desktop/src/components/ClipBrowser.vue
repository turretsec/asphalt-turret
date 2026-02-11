<script setup lang="ts">
import Button from 'primevue/button';
import Checkbox from 'primevue/checkbox';
import Skeleton from 'primevue/skeleton';
import { ref, watch } from 'vue';
import type { Clip } from '../api/types';

const props = defineProps<{
  clips: Clip[];
  loading: boolean;
  error: string | null;
  selectedId: number | null;
}>();

const emit = defineEmits<{
  (e: "select", clip: Clip): void;
  (e: "selection-change", clips: Clip[]): void;
  (e: "load"): void;
}>();

const selectedClips = ref<Clip[]>([]);

// Watch for selection changes and emit
watch(selectedClips, (newSelection) => {
  emit("selection-change", newSelection);
}, { deep: true });

// Handle clicking on the row (not the checkbox)
function onClipClick(clip: Clip, event: MouseEvent) {
  // If they clicked the checkbox area, ignore (let checkbox handle it)
  if ((event.target as HTMLElement).closest('.clip-checkbox')) {
    return;
  }
  
  // Single click to preview
  emit("select", clip);
}

// Check if a clip is selected for preview
function isPreviewedClip(clip: Clip): boolean {
  return props.selectedId === clip.id;
}

// Check if a clip is checked
function isCheckedClip(clip: Clip): boolean {
  return selectedClips.value.some(c => c.id === clip.id);
}
</script>

<template>
  <div class="h-full flex flex-col w-full">
    <div class="p-3 border-b border-surface-800 flex items-center justify-between">
      <div class="font-semibold">
        Clips 
        <span v-if="selectedClips.length > 0" class="text-xs opacity-70 ml-2">
          ({{ selectedClips.length }} selected)
        </span>
      </div>
      <Button 
        class="min-w-20 rounded-md border border-surface-700 hover:bg-surface-900"
        icon="pi pi-refresh"
        @click="emit('load')"
        :disabled="loading"
        :loading="loading"
        size="small"
      >
        {{ loading ? "Loading..." : "Refresh" }}
      </Button>
    </div>

    <div v-if="error" class="p-3 text-red-300 bg-red-950/30 border-b border-red-900">
      {{ error }}
    </div>

    <div v-if="!error && clips.length === 0" class="p-3 opacity-70">
      No clips found.
    </div>

    <div v-if="loading" class="flex flex-col p-3 space-y-2">
      <Skeleton class="min-h-10 max-h-10" />
      <Skeleton class="min-h-10 max-h-10" />
      <Skeleton class="min-h-10 max-h-10" />
      <Skeleton class="min-h-10 max-h-10" />
    </div>

    <ul v-if="!loading" class="flex-1 overflow-auto">
      <li
        v-for="c in clips"
        :key="c.id"
        class="p-3 border-b border-surface-800 hover:bg-surface-900 cursor-pointer transition-colors flex items-center gap-3"
        :class="{
          'bg-blue-950': isPreviewedClip(c) && !isCheckedClip(c),
          'bg-yellow-950': isCheckedClip(c) && !isPreviewedClip(c),
          'bg-cyan-950': isCheckedClip(c) && isPreviewedClip(c),
        }"
        @click="onClipClick(c, $event)"
      >
        <!-- Checkbox for selection -->
        <div class="clip-checkbox flex-shrink-0" @click.stop>
          <Checkbox
            v-model="selectedClips"
            :value="c"
            :inputId="`clip-${c.id}`"
          />
        </div>

        <!-- Clip info -->
        <div class="flex-1 min-w-0">
          <div class="text-sm truncate">{{ c.original_filename }}</div>
          <div class="text-xs opacity-70 mt-1">
            {{ new Date(c.imported_at).toLocaleString() }}
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.clip-checkbox {
  /* Prevent clicks from bubbling to the row */
  pointer-events: auto;
}
</style>