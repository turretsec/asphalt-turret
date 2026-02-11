import { apiGet, API_BASE } from "./client";
import type { Volume } from "./types";

export async function listVolumes(): Promise<Volume[]> {
  return apiGet("/volumes");
}