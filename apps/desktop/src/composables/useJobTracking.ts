import { ref, computed, watch } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { getJobStatus } from '../api/jobs';
import { JobState } from '../api/types';

/**
 * Track a single job with automatic polling.
 * Polls every 1 second while job is pending/running.
 * Stops polling when job completes/fails.
 */
export function useJobTracking(jobId: number | null) {
  const enabled = computed(() => jobId !== null);

  const query = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      // Poll every 1 second while active
      if (state === JobState.PENDING || state === JobState.RUNNING) {
        return 1000;
      }
      // Stop polling when done
      return false;
    },
    refetchOnWindowFocus: false, // Don't spam on tab switch
  });

  const job = computed(() => query.data.value);
  const isActive = computed(() => 
    job.value?.state === JobState.PENDING || 
    job.value?.state === JobState.RUNNING
  );
  const isComplete = computed(() => job.value?.state === JobState.COMPLETED);
  const isFailed = computed(() => job.value?.state === JobState.FAILED);
  
  const progressPercent = computed(() => {
    if (!job.value?.total) return 0;
    return Math.round((job.value.progress / job.value.total) * 100);
  });

  return {
    query,
    job,
    isActive,
    isComplete,
    isFailed,
    progressPercent,
  };
}