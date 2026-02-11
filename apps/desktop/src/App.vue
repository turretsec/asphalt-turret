<script setup lang="ts">
import { ref } from "vue";
import ClipList from "./components/ClipList.vue";
import ClipPlayer from "./components/ClipPlayer.vue";
import Shell from "./layout/Shell.vue";
import type { Clip } from "./api/types";

const selectedClip = ref<Clip | null>(null);
</script>

<template>
  <Shell />
</template>