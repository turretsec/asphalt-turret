<script setup lang="ts" generic="T extends { id: number }">
import Button from 'primevue/button';
import Checkbox from 'primevue/checkbox';
import Skeleton from 'primevue/skeleton';
import Select from 'primevue/select';
import VirtualScroller from 'primevue/virtualscroller';
import { ref, watch, computed, shallowRef } from 'vue';
import { useKeyboardShortcuts } from '../../composables/useKeyboardShortcuts';
import EmptyState from './EmptyState.vue';

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
  actionBarMode?: 'clips' | 'files';
}>();

const emit = defineEmits<{
  (e: "select", item: T): void;
  (e: "selection-change", items: T[]): void;
  (e: "load"): void;
  (e: "toggle-view"): void;
  (e: "delete-selected"): void;
  (e: "sort-change", value: string): void;
  (e: "export"): void;
  (e: "delete"): void;
  (e: "import"): void;
}>();

// Selection state

const selectedItems = shallowRef<T[]>([]);
const focusedIndex = ref<number>(-1);
const lastClickedIndex = ref<number>(-1);

watch(selectedItems, (newSelection) => {
  emit("selection-change", newSelection as T[]);
}, { deep: true });

watch(focusedIndex, (newIndex) => {
  if (newIndex >= 0 && newIndex < props.items.length) {
    emit("select", props.items[newIndex]);
  }
});

// Virtual Scroller

// Ref to the VirtualScroller instance so we can call scrollToIndex() for
// keyboard navigation — getElementById won't work on virtualised items.
const virtualScrollerRef = ref<InstanceType<typeof VirtualScroller> | null>(null);

// Item height must match the actual rendered height per view mode.
// These correspond to padding + content + 1px border-b for each mode:
//   table:    p-2  (8×2) + 1px border + ~20px single-line text  ≈ 37px
//   compact:  p-3 (12×2) + 1px border + h-16 thumbnail (64px)   ≈ 89px
//   expanded: p-4 (16×2) + 1px border + h-28 thumbnail (112px)  ≈ 145px
// Tweak by a few px if items look clipped or have gaps after real-world testing.
const itemSize = computed(() => {
  if (props.viewMode === 'table') return 37;
  if (props.viewMode === 'expanded') return 145;
  return 89; // compact (default)
});

// Item interactions

function onImportClick() {
  emit('import');
  selectedItems.value = [];
  lastClickedIndex.value = -1;
  focusedIndex.value = -1;
}

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

function onItemClick(item: T, event: MouseEvent, index: number) {
  if ((event.target as HTMLElement).closest('.item-checkbox')) return;

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

// Keyboard navigation

useKeyboardShortcuts([
  {
    key: 'ArrowDown',
    description: 'Navigate down',
    handler: () => {
      if (props.items.length === 0) return;
      if (focusedIndex.value === -1) {
        focusedIndex.value = 0;
      } else if (focusedIndex.value < props.items.length - 1) {
        focusedIndex.value++;
      }
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
      if (isCheckedItem(item)) {
        selectedItems.value = selectedItems.value.filter(i => i.id !== item.id);
      } else {
        selectedItems.value = [...selectedItems.value, item];
      }
    }
  }
]);

// VirtualScroller doesn't keep off-screen items in the DOM, so we can't
// use getElementById. Use the scroller's own scrollToIndex() instead.
function scrollToFocused() {
  if (focusedIndex.value < 0) return;
  virtualScrollerRef.value?.scrollToIndex(focusedIndex.value);
}

// Expose

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

      <div class="flex gap-2 items-center">
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

    <!-- Error state -->
    <div v-if="error" class="p-3 text-red-300 bg-red-950/30 border-b border-red-900 flex-shrink-0">
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-if="!error && !loading && items.length === 0" class="flex-1 flex items-center justify-center">
      <slot name="empty">
        <EmptyState
          icon="pi pi-inbox"
          title="No items found"
          description="Try adjusting your filters or search query."
        />
      </slot>
    </div>

    <!-- Loading state -->
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

    <!-- Items list -->
    <div v-if="!loading && items.length > 0" class="flex-1 relative overflow-hidden">

      <!--
        VirtualScroller keeps only the visible slice of items in the DOM.
        At 200 SD files in compact view (~89px each, ~600px viewport) that's
        roughly 7-8 rendered items instead of 200 — so 7 thumbnail requests
        instead of 200. As you scroll, old items unmount and new ones mount.

        scrollHeight="flex" fills the parent container height automatically.
        :itemSize must match the rendered height per viewMode (see computed).
      -->
      <VirtualScroller
        ref="virtualScrollerRef"
        :items="items"
        :itemSize="itemSize"
        scrollHeight="flex"
        class="h-full
          [&::-webkit-scrollbar]:w-2
          [&::-webkit-scrollbar-track]:bg-gray-100
          [&::-webkit-scrollbar-thumb]:bg-gray-300
          dark:[&::-webkit-scrollbar-track]:bg-neutral-700
          dark:[&::-webkit-scrollbar-thumb]:bg-neutral-500"
      >
        <template #item="{ item, index }">
          <li
            :class="[
              itemClass,
              'border-b border-surface-800 hover:bg-surface-800 cursor-pointer transition-colors flex items-center gap-3 w-full list-none',
              { 'bg-surface-700 focus-ring': isFocusedItem(item) }
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
              <div class="flex-1">Item {{ item.id }}</div>
            </slot>
          </li>
        </template>
      </VirtualScroller>

      <!-- Floating Action Bar -->
      <Transition name="slide-up">
        <div
          v-if="selectionCount > 0 && actionBarMode"
          class="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface-800 border border-surface-700 rounded-lg shadow-2xl px-6 py-3 flex items-center gap-4 z-50 w-fit"
        >
          <div class="text-sm font-medium">
            {{ selectionCount }} {{ actionBarMode === 'clips' ? 'clip' : 'file' }}{{ selectionCount > 1 ? 's' : '' }} selected
          </div>

          <div class="h-6 w-px bg-surface-600"></div>

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

          <template v-else>
            <Button
              label="Import"
              icon="pi pi-upload"
              @click="onImportClick"
              severity="success"
              size="small"
            />
          </template>

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

    </div><!-- End items container -->
  </div>
</template>

<style scoped>
.item-checkbox {
  pointer-events: auto;
}

/* Prevent text selection during shift-click */
:deep(.p-virtualscroller) {
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