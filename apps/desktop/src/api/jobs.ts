import { API_BASE } from './client';
import type { JobStatus } from './types';

export async function getJobStatus(jobId: number): Promise<JobStatus> {
  const response = await fetch(`${API_BASE}/imports/jobs/${jobId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }
  
  return response.json();
}