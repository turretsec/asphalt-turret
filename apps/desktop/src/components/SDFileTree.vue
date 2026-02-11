<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import Tree from 'primevue/tree';
import type { TreeNode } from 'primevue/treenode';
import { getSDCardTree } from '../api/sd_card';

const props = defineProps<{
  volumeUid: string;
}>();

const emit = defineEmits<{
  (e: 'selectMode', mode: string): void;
  (e: 'selectDate', payload: { mode: string; date: string }): void;
}>();

const nodes = ref<TreeNode[]>([]);
const loading = ref(false);
import type { TreeSelectionKeys } from 'primevue/tree';

const selectedKey = ref<TreeSelectionKeys>({});

async function loadTree() {
  loading.value = true;
  
  try {
    nodes.value = await getSDCardTree(props.volumeUid);
  } catch (e) {
    console.error('Failed to load tree:', e);
  } finally {
    loading.value = false;
  }
}

function onNodeSelect(node: TreeNode) {
  const data = node.data as any;
  
  if (data.type === 'mode') {
    emit('selectMode', data.mode);
  } else if (data.type === 'date') {
    emit('selectDate', { mode: data.mode, date: data.date });
  }
}

watch(() => props.volumeUid, () => {
  loadTree();
}, { immediate: true });
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="p-3 border-b">
      <h3 class="font-semibold">SD Card Files</h3>
    </div>
    
    <div v-if="loading" class="p-3">Loading...</div>
    
    <div v-else class="flex-1 overflow-auto p-3">
      <Tree
        :value="nodes"
        v-model:selectionKeys="selectedKey"
        selectionMode="single"
        @node-select="onNodeSelect"
      >
        <template #default="{ node }">
          <span>{{ node.label }}</span>
        </template>
      </Tree>
    </div>
  </div>
</template>