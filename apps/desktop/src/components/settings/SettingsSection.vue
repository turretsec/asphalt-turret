<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="space-y-4">
    <!-- Section Header -->
    <div>
      <div class="font-semibold text-sm">{{ title }}</div>
      <p v-if="description" class="text-sm text-surface-400 mt-1">
        {{ description }}
      </p>
    </div>

    <!-- Section Content (slot) -->
    <div class="space-y-4 pl-4 border-l-2 border-surface-800">
      <slot />
    </div>
  </div>
</template>