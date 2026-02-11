<script setup lang="ts">
import { onMounted, ref } from "vue";
import { API_BASE } from "../api/client";
import type { Clip } from "../api/types";

const emit = defineEmits<{
  (e: "select", clip: Clip): void;
}>();

const clips = ref<Clip[]>([]);
const loading = ref(false);
const error = ref<string>("");

async function loadClips(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch(`${API_BASE}/clips`);
    if (!res.ok) throw new Error(`GET /clips failed: ${res.status}`);
    clips.value = (await res.json()) as Clip[];
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadClips);
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="p-3 border-b border-surface-800 flex items-center justify-between">
      <div class="font-semibold">Clips</div>
      <button class="px-3 py-1 rounded-md border border-surface-700 hover:bg-surface-900" @click="loadClips" :disabled="loading">
        {{ loading ? "Loading..." : "Refresh" }}
      </button>
    </div>

    <div v-if="error" class="p-3 text-red-300 bg-red-950/30 border-b border-red-900">
      {{ error }}
    </div>

    <div v-if="!error && clips.length === 0" class="p-3 opacity-70">
      No clips found.
    </div>

    <ul class="flex-1 overflow-auto">
      <li
        v-for="c in clips"
        :key="c.id"
        class="p-3 border-b border-surface-800 hover:bg-surface-900 cursor-pointer"
        @click="emit('select', c)"
      >
        <div class="text-sm">{{ c.original_filename }}</div>
        <div class="text-xs opacity-70 mt-1">{{ new Date(c.imported_at).toLocaleString() }}</div>
      </li>
    </ul>
  </div>
</template>
