<script setup lang="ts">
defineProps<{
  label: string;
  description?: string;
}>();
</script>

<template>
  <div class="flex items-center justify-between py-3">
    <!-- Label & Description -->
    <div class="flex-1 pr-8">
      <div class="font-medium">{{ label }}</div>
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