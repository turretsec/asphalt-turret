import { apiGet, apiPatch } from "./client";
import { SettingsResponse } from "./types";

export function getSettings() {
  return apiGet<SettingsResponse>("/api/settings");
}

export function patchSettings(patch: Record<string, any>) {
  return apiPatch<SettingsResponse>("/api/settings", patch);
}