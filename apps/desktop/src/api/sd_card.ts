import { apiGet, API_BASE } from "./client";
import type { SDFile, SDCard } from "./types";

export async function listSDCardFiles(volume_uid: string): Promise<SDFile[]> {
  return apiGet(`/sd-card/${volume_uid}/files`);
}

export function listSDCards(): Promise<SDCard[]> {
  return apiGet("/sd-card");
}

export async function getSDCardTree(volume_uid: string): Promise<any> {
  return apiGet(`/sd-card/${volume_uid}/tree`);
}