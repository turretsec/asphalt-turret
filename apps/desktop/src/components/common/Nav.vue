<script setup lang="ts">

import PanelMenu from "primevue/panelmenu";

const emit = defineEmits<{
  (e: "select", mode: "repo" | "import" | "settings"): void;
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
  {
    label: "Settings",
    icon: "pi pi-cog",
    command: () => emit("select", "settings"),
  }
];

</script>

<template>
    <PanelMenu :model="items" class="border-none" />
</template>