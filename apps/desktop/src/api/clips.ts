import { apiGet, API_BASE } from "./client";
import type { Clip } from "./types";

export async function listRepoClips(): Promise<Clip[]> {
  return apiGet("/clips");
}

export function clipStreamUrl(id: number): string {
    return `${API_BASE}/clips/${id}/stream`;
}