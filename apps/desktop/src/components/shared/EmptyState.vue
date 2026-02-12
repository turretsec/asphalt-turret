<script setup lang="ts">
/**
 * Reusable empty state component with icon, title, description, and optional action.
 */

defineProps<{
  icon: string;           // PrimeVue icon class (e.g., 'pi pi-inbox')
  title: string;          // Main message
  description?: string;   // Optional explanation
  actionLabel?: string;   // Optional button text
}>();

const emit = defineEmits<{
  (e: "action"): void;
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-8 text-center">
    <!-- Icon -->
    <div class="w-20 h-20 rounded-full bg-surface-800 flex items-center justify-center mb-6">
      <i :class="icon" class="text-4xl text-surface-400"></i>
    </div>

    <!-- Title -->
    <h3 class="text-xl font-semibold mb-2">
      {{ title }}
    </h3>

    <!-- Description -->
    <p v-if="description" class="text-surface-400 max-w-md mb-6">
      {{ description }}
    </p>

    <!-- Action Button -->
    <Button
      v-if="actionLabel"
      :label="actionLabel"
      @click="emit('action')"
      severity="secondary"
      outlined
    />
  </div>
</template>