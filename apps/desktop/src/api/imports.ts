import { apiGet } from "./client";
import type { SDFile } from "./types";
import { ImportRequest, ImportResponse } from "./types";

export const API_BASE = "http://127.0.0.1:8000";

export async function importSDFiles(request: ImportRequest): Promise<ImportResponse> {
  const response = await fetch(`${API_BASE}/imports/sd-card`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Import failed: ${response.statusText}`);
  }
  
  return response.json();
}