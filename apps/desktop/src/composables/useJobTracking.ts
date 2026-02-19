import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { getJobStatus } from '../api/jobs';
import { JobState } from '../api/types';

/**
 * Track a single job with automatic polling.
 * Polls every 1 second while the job is active or not yet loaded.
 * Stops polling once the job reaches a terminal state (completed/failed).
 */
export function useJobTracking(jobId: number | null) {
  const enabled = computed(() => jobId !== null);

  const query = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled,
    refetchInterval: (query) => {
      const state = query.state.data?.state;

      // If we haven't fetched yet (undefined), keep polling — the job was
      // just created and we need to get its initial state.
      if (state === undefined) return 1000;

      // Poll while the job is active
      if (state === JobState.QUEUED || state === JobState.RUNNING) return 1000;

      // Terminal state — stop polling
      return false;
    },
    refetchOnWindowFocus: false,
  });

  const job = computed(() => query.data.value);

  const isActive = computed(() =>
    job.value?.state === JobState.QUEUED ||
    job.value?.state === JobState.RUNNING
  );
  const isComplete = computed(() => job.value?.state === JobState.COMPLETED);
  const isFailed = computed(() => job.value?.state === JobState.FAILED);

  const progressPercent = computed(() => job.value?.progress ?? 0);

  return {
    query,
    job,
    isActive,
    isComplete,
    isFailed,
    progressPercent,
  };
}