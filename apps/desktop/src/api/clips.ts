import { apiGet, API_BASE } from "./client";
import type { Clip, DeleteClipsRequest, DeleteClipsResponse, ExportClipsRequest, ExportClipsResponse } from "./types";

export async function listRepoClips(): Promise<Clip[]> {
  return apiGet("/clips");
}

export function clipStreamUrl(id: number): string {
    return `${API_BASE}/clips/${id}/stream`;
}

export async function deleteClips(request: DeleteClipsRequest): Promise<DeleteClipsResponse> {
  const response = await fetch(`${API_BASE}/clips`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete clips');
  }
  
  return response.json();
}


export async function exportClips(request: ExportClipsRequest): Promise<ExportClipsResponse> {
  const response = await fetch(`${API_BASE}/clips/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to export clips');
  }
  
  return response.json();
}