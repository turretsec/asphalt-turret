<script lang="ts" setup>
import Toolbar from 'primevue/toolbar';
import SearchBox from './toolbar/SearchBox.vue';

import SelectButton from "primevue/selectbutton";
import MultiSelect from "primevue/multiselect";
import type { SDFileImportState, DatePreset, ImportFilters } from "../api/types";
import DatePicker from 'primevue/datepicker';

const props = defineProps<{
  query: string;
}>();

const emit = defineEmits<{
  (e: "update:query", value: string): void;
}>();

// v-model bindings coming from ImportView
const modes = defineModel<string[]>("modes");
const states = defineModel<SDFileImportState[]>("states");
const datePreset = defineModel<DatePreset>("datePreset");
const dateRange = defineModel<[Date, Date] | null>("dateRange");


const modeOptions = [
  { label: "Continuous", value: "continuous" },
  { label: "Event", value: "event" },
  { label: "Parking", value: "parking" },
  { label: "Unknown", value: "unknown" },
];

const stateOptions: { label: string; value: SDFileImportState }[] = [
  { label: "New", value: "new" as SDFileImportState },
  { label: "Imported", value: "imported" as SDFileImportState },
  { label: "Queued", value: "queued" as SDFileImportState },
  { label: "Failed", value: "failed" as SDFileImportState },
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
    <div class="flex flex-col items-center w-full bg-surface-900 border-b border-surface-700 p-2 gap-2">
        <div class="flex flex-row gap-2 w-full">

        
        <SearchBox 
            :query="props.query"
            @update:query="(v) => emit('update:query', String(v))"
        />
        </div>

    </div>
</template>