<script setup lang="ts">
import ProgressBar from 'primevue/progressbar';
import Message from 'primevue/message';
import Button from 'primevue/button';
import { useJobTracking } from '../../composables/useJobTracking';
import { useActiveJobs } from '../../composables/useActiveJobs';
import { watch, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { JobState } from '../../api/types';

const props = defineProps<{
  jobId: number;
  showToastOnComplete?: boolean;
}>();

const emit = defineEmits<{
  (e: 'complete'): void;
  (e: 'failed', error: string): void;
  (e: 'dismiss'): void;
}>();

const toast = useToast();
const { removeJob } = useActiveJobs();
const { job, isComplete, isFailed, progressPercent } = useJobTracking(props.jobId);

// Import stats directly from job response
const importStats = computed(() => {
  if (!job.value) return null;
  
  return {
    total: job.value.total || 0,
    completed: job.value.completed || 0,
    failed: job.value.failed || 0,
  };
});

// Watch for completion
watch(isComplete, (complete) => {
  if (complete) {
    removeJob(props.jobId);
    
    if (props.showToastOnComplete) {
      const stats = importStats.value;
      
      if (stats && stats.total > 0) {
        // All succeeded
        if (stats.failed === 0) {
          toast.add({
            severity: 'success',
            summary: 'Import Complete',
            detail: `Successfully imported ${stats.completed} file${stats.completed > 1 ? 's' : ''}`,
            life: 3000,
          });
        }
        // Some failed
        else if (stats.completed > 0) {
          toast.add({
            severity: 'warn',
            summary: 'Import Partially Complete',
            detail: `Imported ${stats.completed} file${stats.completed > 1 ? 's' : ''}, ${stats.failed} failed`,
            life: 5000,
          });
        }
        // All failed
        else {
          toast.add({
            severity: 'error',
            summary: 'Import Failed',
            detail: `All ${stats.total} file${stats.total > 1 ? 's' : ''} failed to import`,
            life: 5000,
          });
        }
      } else {
        // Fallback if no stats
        toast.add({
          severity: 'success',
          summary: 'Import Complete',
          detail: job.value?.message || 'Job completed successfully',
          life: 3000,
        });
      }
    }
    
    emit('complete');
  }
});

// Watch for failure (job-level failure)
watch(isFailed, (failed) => {
  if (failed) {
    removeJob(props.jobId);
    
    toast.add({
      severity: 'error',
      summary: 'Import Failed',
      detail: job.value?.message || 'Job failed to process',
      life: 5000,
    });
    
    emit('failed', job.value?.message || 'Unknown error');
  }
});

function handleDismiss() {
  removeJob(props.jobId);
  emit('dismiss');
}

onMounted(() => {
  console.log('JobProgress mounted with jobId:', props.jobId);
});

watch(job, (newJob) => {
  console.log('Job updated:', newJob);  // ← ADD THIS
}, { immediate: true });
</script>

<template>
  <div v-if="job" class="space-y-2">
    <!-- Failed state (job-level failure) -->
    <Message v-if="job.state === JobState.FAILED" severity="error" :closable="false">
      <div class="flex items-center justify-between w-full">
        <div class="flex-1">
          <div class="font-semibold">Import Failed</div>
          <div class="text-sm mt-1">{{ job.message || 'Unknown error occurred' }}</div>
        </div>
        <Button
          icon="pi pi-times"
          text
          rounded
          severity="secondary"
          @click="handleDismiss"
        />
      </div>
    </Message>

    <!-- Completed state -->
    <Message 
      v-else-if="job.state === JobState.COMPLETED" 
      :severity="importStats && importStats.failed > 0 ? 'warn' : 'success'"
      :closable="false"
    >
      <div class="flex items-center justify-between w-full">
        <div class="flex-1">
          <div class="font-semibold">
            {{ importStats && importStats.failed > 0 ? 'Import Partially Complete' : 'Import Complete' }}
          </div>
          <div class="text-sm mt-1">
            <template v-if="importStats && importStats.total > 0">
              <span v-if="importStats.failed === 0">
                Successfully imported {{ importStats.completed }} file{{ importStats.completed > 1 ? 's' : '' }}
              </span>
              <span v-else>
                Imported {{ importStats.completed }} file{{ importStats.completed > 1 ? 's' : '' }}, 
                {{ importStats.failed }} failed
              </span>
            </template>
            <template v-else>
              {{ job.message || 'Import completed' }}
            </template>
          </div>
        </div>
        <Button
          icon="pi pi-times"
          text
          rounded
          severity="secondary"
          @click="handleDismiss"
        />
      </div>
    </Message>

    <!-- Active state (queued/running) -->
    <div v-else>
      <!-- Progress info -->
      <div class="flex justify-between text-sm items-center">
        <span>{{ job.message || 'Processing...' }}</span>
        <div class="flex items-center gap-2">
          <span v-if="importStats && importStats.total > 0">
            {{ importStats.completed }}/{{ importStats.total }}
          </span>
          <Button
            icon="pi pi-times"
            text
            rounded
            size="small"
            severity="secondary"
            @click="handleDismiss"
            v-tooltip.left="'Dismiss (job continues in background)'"
          />
        </div>
      </div>
      
      <!-- Progress bar -->
      <ProgressBar 
        :value="progressPercent" 
        :showValue="false"
        class="h-2"
      />
      
      <!-- State indicator -->
      <div class="text-xs text-surface-400 mt-1">
        {{ job.state === JobState.QUEUED ? 'Queued...' : 'Running...' }}
      </div>
    </div>
  </div>
</template>