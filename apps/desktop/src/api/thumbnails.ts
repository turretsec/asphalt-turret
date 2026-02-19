import { API_BASE } from './client';

export function getClipThumbnailUrl(clipId: number): string {
  return `${API_BASE}/clips/${clipId}/thumbnail`;
}

export function getSDFileThumbnailUrl(volumeUid: string, fileId: number): string {
  return `${API_BASE}/sd-card/${volumeUid}/files/${fileId}/thumbnail`;
}