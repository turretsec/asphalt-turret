<script setup lang="ts">
import MultiSelect from "primevue/multiselect";
import DatePicker from 'primevue/datepicker';
import Select from "primevue/select";
import InputText from "primevue/inputtext";
import { ModeEnum } from "../../api/types";
import type { DatePreset } from "../../api/types";

// SHARED filters
const query = defineModel<string>("query");
const modes = defineModel<ModeEnum[]>("modes");
const datePreset = defineModel<DatePreset>("datePreset");
const dateRange = defineModel<[Date, Date] | null>("dateRange");

const modeOptions: { label: string; value: ModeEnum }[] = [
  { label: "Continuous", value: ModeEnum.CONTINUOUS },
  { label: "Event", value: ModeEnum.EVENT },
  { label: "Parking", value: ModeEnum.PARKING },
  { label: "Unknown", value: ModeEnum.UNKNOWN },
];

const datePresets: { label: string; value: DatePreset }[] = [
  { label: "All", value: "all" },
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "7 days", value: "7d" },
  { label: "Custom", value: "custom" },
];
</script>

<template>
  <div class="flex flex-col items-center w-full bg-surface-900 p-2 gap-2 border-t border-surface-700">
    <!-- Search (shared) -->
    <InputText
      v-model="query"
      placeholder="Search..."
      class="flex w-full"
      size="small"
    />

    <!-- Mode filter (shared) -->
    <MultiSelect
      v-model="modes"
      :options="modeOptions"
      optionLabel="label"
      optionValue="value"
      placeholder="Modes"
      class="flex w-full"
      display="chip"
      size="small"
      :pt="{
        label: { class: 'flex flex-col gap-1 items-start' },
      }"
    />

    <!-- SLOT: View-specific filters -->
    <slot name="filters"></slot>

    <!-- Date filters (shared) -->
    <Select
      v-model="datePreset"
      :options="datePresets"
      optionLabel="label"
      optionValue="value"
      class="flex w-full"
      size="small"
    />
    
    <DatePicker
      v-if="datePreset === 'custom'"
      v-model="dateRange"
      selectionMode="range"
      placeholder="Date range"
      class="flex w-full"
      size="small"
      :pt="{
        root: { class: 'flex flex-col gap-1' },
        InputText: { class: 'flex w-full' },
      }"
    />

    <!-- SLOT: Action buttons -->
    <slot name="actions"></slot>
  </div>
</template>