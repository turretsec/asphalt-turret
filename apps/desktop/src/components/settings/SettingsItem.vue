<script setup lang="ts">
defineProps<{
  label: string;
  description?: string;
}>();
</script>

<template>
  <div class="flex flex-col justify-between gap-2">
    <!-- Label & Description -->
    <div class="flex flex-col">
      <div class="text-sm">{{ label }}</div>
      <div v-if="description" class="text-sm text-surface-400 mt-1">
        {{ description }}
      </div>
    </div>

    <!-- Control (slot) -->
    <div class="flex-shrink-0">
      <slot />
    </div>
  </div>
</template>