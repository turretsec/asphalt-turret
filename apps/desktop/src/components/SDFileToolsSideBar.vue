<script lang="ts" setup>
import MultiSelect from "primevue/multiselect";
import DatePicker from 'primevue/datepicker';
import Select from "primevue/select";
import Button from "primevue/button";
import { ModeEnum } from "../api/types";
import { computed } from 'vue';
import { SDFileImportState } from "../api/types";
import type { DatePreset, SDFile } from "../api/types";


const emit = defineEmits<{
  (e: "import"): void;
}>();


const modeOptions: { label: string; value: ModeEnum }[] = [
  { label: "Continuous", value: ModeEnum.CONTINUOUS },
  { label: "Event", value: ModeEnum.EVENT },
  { label: "Parking", value: ModeEnum.PARKING },
  { label: "Unknown", value: ModeEnum.UNKNOWN },
];

const stateOptions: { label: string; value: SDFileImportState }[] = [
  { label: "New", value: SDFileImportState.NEW},
  { label: "Imported", value: SDFileImportState.IMPORTED },
  { label: "Pending", value: SDFileImportState.PENDING },
  { label: "Failed", value: SDFileImportState.FAILED },
];

const datePresets: { label: string; value: DatePreset }[] = [
  { label: "All", value: "all" },
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "7 days", value: "7d" },
  { label: "Custom", value: "custom" },
];

const modes = defineModel<ModeEnum[]>("modes");
const states = defineModel<SDFileImportState[]>("states");
const datePreset = defineModel<DatePreset>("datePreset");
const dateRange = defineModel<[Date, Date] | null>("dateRange");


const props = defineProps<{
  selectedFiles: SDFile[];
  volumeUid: string;
}>();


const canImport = computed(() => props.selectedFiles.length > 0);
const importButtonLabel = computed(() => {
  const count = props.selectedFiles.length;
  return count > 0 ? `Import ${count} file${count > 1 ? 's' : ''}` : 'Import';
});

</script>
<template>
    <div class="flex flex-col items-center w-full bg-surface-900 border-b border-surface-700 p-2 gap-2">
        <MultiSelect
            v-model="modes"
            :options="modeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Modes"
            class="flex w-full"
            display="chip"
            size="small"
        />

        <MultiSelect
            v-model="states"
            :options="stateOptions"
            optionLabel="label"
            optionValue="value"
            display="chip"
            placeholder="State"
            class="flex w-full"
            size="small"
        />

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
        />

        <Button
        :label="importButtonLabel"
        :disabled="!canImport"
        @click="emit('import')"
        severity="success"
        class="flex w-full mt-2"
        size="small"
        />
    </div>

</template>