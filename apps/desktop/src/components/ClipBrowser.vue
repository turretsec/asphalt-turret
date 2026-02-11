<script setup lang="ts">
import Button from 'primevue/button';
import Skeleton from 'primevue/skeleton';

import type { Clip } from '../api/types';

const emit = defineEmits<{
  (e: "select", clip: Clip): void;
  (e: "load"): void;
}>();

defineProps<{
  clips: Clip[];
  loading: boolean;
  error: string | null;
  selectedId: number | null;
}>();

</script>

<template>
  <div class="h-full flex flex-col w-full">
    <div class="p-3 border-b border-surface-800 flex items-center justify-between">
      <div class="font-semibold">Clips</div>
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
        class="p-3 border-b border-surface-800 hover:bg-surface-500 cursor-pointer"
        :class="{
          'bg-primary-500': selectedId === c.id,
        }"
        @click="emit('select', c)"
      >
        <div class="text-sm">{{ c.original_filename }}</div>
        <div class="text-xs opacity-70 mt-1">{{ new Date(c.imported_at).toLocaleString() }}</div>
      </li>
    </ul>
  </div>
</template>