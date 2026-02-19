<script setup lang="ts" generic="T extends { id: number }">
import Button from 'primevue/button';
import Checkbox from 'primevue/checkbox';
import Skeleton from 'primevue/skeleton';
import Select from 'primevue/select';
import { ref, watch, computed, shallowRef } from 'vue';
import { useKeyboardShortcuts } from '../../composables/useKeyboardShortcuts';
import EmptyState from './EmptyState.vue';
import Tooltip from 'primevue/tooltip';

export type SortOption = {
  label: string;
  value: string;
};

const props = defineProps<{
  items: T[];
  loading: boolean;
  error: string | null;
  selectedId: number | null;
  title: string;
  viewMode?: 'compact' | 'expanded' | 'table';
  sortOptions?: SortOption[];
  sortBy?: string;
  actionBarMode?: 'clips' | 'files';  // ← NEW
}>();

const emit = defineEmits<{
  (e: "select", item: T): void;
  (e: "selection-change", items: T[]): void;
  (e: "load"): void;
  (e: "toggle-view"): void;
  (e: "delete-selected"): void;
  (e: "sort-change", value: string): void;
  (e: "export"): void;  // ← NEW
  (e: "delete"): void;  // ← NEW
  (e: "import"): void;  // ← NEW
}>();

// Two types of selection:
// 1. focusedIndex - the highlighted item (for navigation/preview)
// 2. selectedItems - the checked items (for bulk operations)
const selectedItems = shallowRef<T[]>([]);
const focusedIndex = ref<number>(-1);
const lastClickedIndex = ref<number>(-1);

watch(selectedItems, (newSelection) => {
  emit("selection-change", newSelection as T[]);
}, { deep: true });

// Watch focused item and auto-preview it
watch(focusedIndex, (newIndex) => {
  if (newIndex >= 0 && newIndex < props.items.length) {
    emit("select", props.items[newIndex]);
  }
});

// On Import Button click - emit event and clear selection immediately
function onImportClick() {
  emit('import');
  // Clear selection immediately after emitting
  selectedItems.value = [];
  lastClickedIndex.value = -1;
  focusedIndex.value = -1;
}

// Handle checkbox clicks with shift-select support
function onCheckboxClick(item: T, index: number, event: MouseEvent) {
  if (event.shiftKey && lastClickedIndex.value !== -1) {
    event.preventDefault();
    
    const start = Math.min(lastClickedIndex.value, index);
    const end = Math.max(lastClickedIndex.value, index);
    const range = props.items.slice(start, end + 1);
    
    const lastClickedItem = props.items[lastClickedIndex.value];
    const isSelecting = isCheckedItem(lastClickedItem);
    
    if (isSelecting) {
      const newSelection = [...selectedItems.value];
      for (const rangeItem of range) {
        if (!newSelection.some(i => i.id === rangeItem.id)) {
          newSelection.push(rangeItem);
        }
      }
      selectedItems.value = newSelection;
    } else {
      const rangeIds = new Set(range.map(r => r.id));
      selectedItems.value = selectedItems.value.filter(i => !rangeIds.has(i.id));
    }
  } else {
    lastClickedIndex.value = index;
  }
}

// Click on item body - set focus and preview
function onItemClick(item: T, event: MouseEvent, index: number) {
  if ((event.target as HTMLElement).closest('.item-checkbox')) {
    return;
  }

  // Shift-click on item - select range
  if (event.shiftKey && lastClickedIndex.value !== -1) {
    const start = Math.min(lastClickedIndex.value, index);
    const end = Math.max(lastClickedIndex.value, index);
    const range = props.items.slice(start, end + 1);
    
    const newSelection = [...selectedItems.value];
    for (const rangeItem of range) {
      if (!newSelection.some(i => i.id === rangeItem.id)) {
        newSelection.push(rangeItem);
      }
    }
    selectedItems.value = newSelection;
  }
  
  // Always set focus and preview on click
  focusedIndex.value = index;
  lastClickedIndex.value = index;
  emit("select", item);
}

function isFocusedItem(item: T): boolean {
  if (focusedIndex.value === -1) return false;
  return props.items[focusedIndex.value]?.id === item.id;
}

function isCheckedItem(item: T): boolean {
  return selectedItems.value.some(i => i.id === item.id);
}

const selectionCount = computed(() => selectedItems.value.length);

const itemClass = computed(() => {
  if (props.viewMode === 'table') return 'p-2';
  if (props.viewMode === 'expanded') return 'p-4 min-h-24';
  return 'p-3';
});

// Keyboard shortcuts
useKeyboardShortcuts([
  {
    key: 'ArrowDown',
    description: 'Navigate down',
    handler: (e) => {
      if (props.items.length === 0) return;
      
      if (focusedIndex.value === -1) {
        focusedIndex.value = 0;
      } else if (focusedIndex.value < props.items.length - 1) {
        focusedIndex.value++;
      }
      
      // Scroll into view
      scrollToFocused();
    }
  },
  {
    key: 'ArrowUp',
    description: 'Navigate up',
    handler: () => {
      if (props.items.length === 0) return;
      
      if (focusedIndex.value === -1) {
        focusedIndex.value = 0;
      } else if (focusedIndex.value > 0) {
        focusedIndex.value--;
      }
      
      scrollToFocused();
    }
  },
  {
    key: 'a',
    ctrlKey: true,
    description: 'Select all',
    handler: () => {
      if (props.items.length > 0) {
        selectedItems.value = [...props.items];
      }
    }
  },
  {
    key: 'Escape',
    description: 'Clear selection',
    handler: () => {
      selectedItems.value = [];
      lastClickedIndex.value = -1;
    }
  },
  {
    key: 'Delete',
    description: 'Delete selected items',
    handler: () => {
      if (selectedItems.value.length > 0) {
        emit('delete-selected');
      }
    }
  },
  {
    key: ' ',
    description: 'Toggle checkbox on focused item',
    handler: () => {
      if (focusedIndex.value === -1 || props.items.length === 0) return;
      
      const item = props.items[focusedIndex.value];
      const isChecked = isCheckedItem(item);
      
      if (isChecked) {
        selectedItems.value = selectedItems.value.filter(i => i.id !== item.id);
      } else {
        selectedItems.value = [...selectedItems.value, item];
      }
    }
  }
]);

// Scroll focused item into view
function scrollToFocused() {
  setTimeout(() => {
    const element = document.getElementById(`item-${focusedIndex.value}`);
    element?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 0);
}

// Expose method for parent to clear selection
defineExpose({
  clearSelection: () => {
    selectedItems.value = [];
    lastClickedIndex.value = -1;
    focusedIndex.value = -1;
  }
});
</script>

<template>
  <div class="h-full flex flex-col w-full relative overflow-hidden">
    <!-- Header -->
    <div class="p-3 border-b border-surface-800 flex items-center justify-between flex-shrink-0">
      <div class="font-semibold">
        {{ title }}
        <span v-if="selectionCount > 0" class="text-xs opacity-70 ml-2">
          ({{ selectionCount }} selected)
        </span>
      </div>
      
      <!-- Actions -->
      <div class="flex gap-2 items-center">
        <!-- Sort dropdown (if options provided) -->
        <Select
          v-if="sortOptions && sortOptions.length > 0"
          :modelValue="sortBy"
          @update:modelValue="emit('sort-change', $event)"
          :options="sortOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Sort by..."
          class="w-40"
          size="small"
        />
        
        <!-- View mode toggle button -->
        <Button 
          class="aspect-square"
          severity="secondary"
          :icon="
            viewMode === 'table' ? 'pi pi-table' : 
            viewMode === 'compact' ? 'pi pi-list' : 
            'pi pi-th-large'
          "
          @click="emit('toggle-view')"
          size="small"
          v-tooltip.bottom="
            viewMode === 'table' ? 'Compact view' : 
            viewMode === 'compact' ? 'Expanded view' : 
            'Table view'
          "
        />
        
        <!-- Refresh button -->
        <Button 
          class="aspect-square"
          severity="secondary"
          icon="pi pi-refresh"
          @click="emit('load')"
          :disabled="loading"
          :loading="loading"
          size="small"
        />
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="p-3 text-red-300 bg-red-950/30 border-b border-red-900 flex-shrink-0">
      {{ error }}
    </div>

    <!-- Empty State -->
    <div v-if="!error && !loading && items.length === 0" class="flex-1 flex items-center justify-center flex-shrink-0">
      <slot name="empty">
        <EmptyState
          icon="pi pi-inbox"
          title="No items found"
          description="Try adjusting your filters or search query."
        />
      </slot>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col p-3 space-y-2 flex-shrink-0">
      <Skeleton 
        v-for="i in 6"
        :key="i"
        :class="
          viewMode === 'table' ? 'h-8' : 
          viewMode === 'expanded' ? 'h-24' : 
          'h-10'
        " 
      />
    </div>

    <!-- Items List Container -->
    <div v-if="!loading && items.length > 0" class="flex-1 relative overflow-hidden
      ">
      <ul class="h-full overflow-auto
      [&::-webkit-scrollbar]:w-2
      [&::-webkit-scrollbar-track]:bg-gray-100
      [&::-webkit-scrollbar-thumb]:bg-gray-300
      dark:[&::-webkit-scrollbar-track]:bg-neutral-700
      dark:[&::-webkit-scrollbar-thumb]:bg-neutral-500
      ">
        <li
          v-for="(item, index) in items"
          :key="item.id"
          :id="`item-${index}`"
          :class="[
            itemClass,
            'border-b border-surface-800 hover:bg-surface-800 cursor-pointer transition-colors flex items-center gap-3',
            {
              'bg-surface-700 focus-ring': isFocusedItem(item),
            //  'bg-surface-700': isCheckedItem(item) && !isFocusedItem(item),
            //  'bg-surface-700': isCheckedItem(item) && isFocusedItem(item),
            }
          ]"
          @click="onItemClick(item, $event, index)"
        >
          <!-- Checkbox -->
          <div class="item-checkbox flex-shrink-0" @click.stop>
            <Checkbox
              v-model="selectedItems"
              :value="item"
              :inputId="`item-checkbox-${item.id}`"
              @click="onCheckboxClick(item, index, $event)"
            />
          </div>

          <!-- Custom item content -->
          <slot 
            name="item" 
            :item="item"
            :isSelected="isCheckedItem(item)"
            :isPreviewed="isFocusedItem(item)"
            :viewMode="viewMode"
          >
            <div class="flex-1">
              Item {{ item.id }}
            </div>
          </slot>
        </li>
      </ul>

      <!-- Floating Action Bar - MOVED INSIDE items container -->
      <Transition name="slide-up">
        <div 
          v-if="selectionCount > 0 && actionBarMode"
          class="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface-800 border border-surface-700 rounded-lg shadow-2xl px-6 py-3 flex items-center gap-4 z-50 w-fit"
        >
          <!-- Selection count -->
          <div class="text-sm font-medium">
            {{ selectionCount }} {{ actionBarMode === 'clips' ? 'clip' : 'file' }}{{ selectionCount > 1 ? 's' : '' }} selected
          </div>

          <!-- Divider -->
          <div class="h-6 w-px bg-surface-600"></div>

          <!-- Actions for clips -->
          <template v-if="actionBarMode === 'clips'">
            <Button
              label="Export"
              icon="pi pi-download"
              @click="emit('export')"
              severity="info"
              size="small"
            />
            <Button
              label="Delete"
              icon="pi pi-trash"
              @click="emit('delete')"
              severity="danger"
              size="small"
            />
          </template>

          <!-- Actions for SD files -->
          <template v-else>
            <Button
              label="Import"
              icon="pi pi-upload"
              @click="onImportClick"
              severity="success"
              size="small"
            />
          </template>

          <!-- Clear selection -->
          <Button
            icon="pi pi-times"
            @click="selectedItems = []"
            severity="secondary"
            size="small"
            text
            v-tooltip.top="'Clear selection (Esc)'"
          />
        </div>
      </Transition>
    </div>  <!-- ← End of items container -->
  </div>
</template>

<style scoped>
.item-checkbox {
  pointer-events: auto;
}

/* Prevent text selection during shift-click */
ul {
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

/* Slide up animation */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from {
  opacity: 0;
  transform: translate(-50%, 20px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 10px);
}
</style>