<script setup lang="ts">
import Menu from "primevue/menu";
import { ref } from "vue";
const emit = defineEmits<{
  (e: "select", mode: "repo" | "import" | "settings"): void;
}>();

const items = ref([
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
]);

</script>

<template>
  <Menu
    :model="items"
    class="border-none bg-surface-950"
    :pt="{
      itemLink: { class: 'flex items-center gap-2' },
      itemIcon: { class: 'leading-none text-sm' },
      itemLabel: { class: 'text-sm leading-none text-surface-200' },
    }"
  />
</template>