<script setup lang="ts">
import Select from 'primevue/select';
import type { SDCard } from '../../api/types';
import { computed } from 'vue';

const props = defineProps<{
  cards: SDCard[];
  currentVolumeUid: string;
}>();

const emit = defineEmits<{
  (e: 'change', volumeUid: string): void;
}>();

// Format card info for dropdown
const cardOptions = computed(() => {
  return props.cards
    .filter(card => card.is_connected)
    .map(card => ({
      label: card.volume_label || card.volume_uid,
      value: card.volume_uid,
      // You could add more info here like capacity if available
    }));
});

function onChange(volumeUid: string) {
  emit('change', volumeUid);
}
</script>

<template>
  <div v-if="cardOptions.length > 0" class="flex items-center gap-2">
    <span class="text-sm text-surface-400">SD Card:</span>
    <Select
      :modelValue="currentVolumeUid"
      @update:modelValue="onChange"
      :options="cardOptions"
      optionLabel="label"
      optionValue="value"
      placeholder="Select SD card"
      class="w-64"
      size="small"
    />
    <span v-if="cardOptions.length > 1" class="text-xs text-surface-400">
      ({{ cardOptions.length }} cards connected)
    </span>
  </div>
</template>