import { ref } from 'vue';

export type ViewMode = 'compact' | 'expanded' | 'table';

export function useViewMode(storageKey: string = 'viewMode') {
  const savedMode = localStorage.getItem(storageKey) as ViewMode | null;
  const viewMode = ref<ViewMode>(savedMode || 'compact');

  function setViewMode(mode: ViewMode) {
    viewMode.value = mode;
    localStorage.setItem(storageKey, mode);
  }

  // Cycle through all three modes
  function toggleViewMode() {
    const modes: ViewMode[] = ['table', 'compact', 'expanded'];
    const currentIndex = modes.indexOf(viewMode.value);
    const nextIndex = (currentIndex + 1) % modes.length;
    setViewMode(modes[nextIndex]);
  }

  return {
    viewMode,
    setViewMode,
    toggleViewMode,
  };
}