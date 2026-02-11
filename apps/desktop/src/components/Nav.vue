<script setup lang="ts">

import PanelMenu from "primevue/panelmenu";

const emit = defineEmits<{
  (e: "select", mode: "repo" | "import"): void;
}>();

const items = [
  {
    label: "Repository",
    icon: "pi pi-database",
    command: () => emit("select", "repo"),
  },
  {
    label: "Import",
    icon: "pi pi-file-import",
    command: () => emit("select", "import"),
  },
];

</script>

<template>
    <PanelMenu :model="items" class="border-none" />
</template>