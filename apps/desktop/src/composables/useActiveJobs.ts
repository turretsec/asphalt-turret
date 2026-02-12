import { ref } from 'vue';

/**
 * Global tracker for active jobs.
 * Components can register jobs here to show progress indicators.
 */
const activeJobs = ref<Set<number>>(new Set());

export function useActiveJobs() {
  function addJob(jobId: number) {
    activeJobs.value.add(jobId);
  }

  function removeJob(jobId: number) {
    activeJobs.value.delete(jobId);
  }

  function hasActiveJobs() {
    return activeJobs.value.size > 0;
  }

  return {
    activeJobs,
    addJob,
    removeJob,
    hasActiveJobs,
  };
}