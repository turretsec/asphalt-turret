import { ref, watch } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import { useSettings } from "./useSettings";
import type { UserSettings } from "../api/types";
import { useToast } from "primevue/usetoast";

type DirKey = keyof Pick<UserSettings, "repository_dir" | "incoming_dir">;
type NumberKey = keyof Pick<UserSettings, "thumbnail_quality" | "thumbnail_width" | "thumbnail_height" | "ffprobe_timeout_s">;

const DEFAULTS = {
  thumbnail_quality: 85,
  thumbnail_width: 320,
  thumbnail_height: 180,
  ffprobe_timeout_s: 30,
} as const;

export function useSettingsDraft() {
  const { effective, save, saving, lastSaveResult, query } = useSettings();
  const toast = useToast();

  // Draft refs (typed)
  const repoDraft = ref<string>("");
  const incomingDraft = ref<string>("");
  const thumbnailQualityDraft = ref<number>(DEFAULTS.thumbnail_quality);
  const thumbnailWidthDraft = ref<number>(DEFAULTS.thumbnail_width);
  const thumbnailHeightDraft = ref<number>(DEFAULTS.thumbnail_height);
  const ffprobeTimeoutDraft = ref<number>(DEFAULTS.ffprobe_timeout_s);

  // Hydrate drafts from effective
  watch(
    () => effective.value,
    (eff) => {
      if (!eff) return;

      repoDraft.value = eff.repository_dir ?? "";
      incomingDraft.value = eff.incoming_dir ?? "";
      thumbnailQualityDraft.value = eff.thumbnail_quality ?? DEFAULTS.thumbnail_quality;
      thumbnailWidthDraft.value = eff.thumbnail_width ?? DEFAULTS.thumbnail_width;
      thumbnailHeightDraft.value = eff.thumbnail_height ?? DEFAULTS.thumbnail_height;
      ffprobeTimeoutDraft.value = eff.ffprobe_timeout_s ?? DEFAULTS.ffprobe_timeout_s;
    },
    { immediate: true }
  );

  // Type-safe save functions
  async function saveKey<K extends keyof UserSettings>(
    key: K, 
    value: UserSettings[K]
  ): Promise<void> {
    try {
      await save({ [key]: value } as Partial<UserSettings>);
    } catch (error) {
      toast.add({
        severity: 'error',
        summary: 'Save Failed',
        detail: error instanceof Error ? error.message : 'Could not save setting',
        life: 5000,
      });
      throw error; // Re-throw so callers know it failed
    }
  }

  async function saveKeys(patch: Partial<UserSettings>): Promise<void> {
    try {
      await save(patch);
    } catch (error) {
      toast.add({
        severity: 'error',
        summary: 'Save Failed',
        detail: error instanceof Error ? error.message : 'Could not save settings',
        life: 5000,
      });
      throw error;
    }
  }

  // Debounced saver (for typing in number inputs)
  const timers = new Map<string, number>();

  function saveKeyDebounced<K extends keyof UserSettings>(
      key: K,
      value: UserSettings[K],
      ms = 350
    ): Promise<void> | void {
      const existing = timers.get(key as string);
      if (existing) window.clearTimeout(existing);
  
      const t = window.setTimeout(async () => {
        try {
          await saveKey(key, value);
        } finally {
          timers.delete(key as string);
        }
      }, ms);
  
      timers.set(key as string, t);
    }

  async function chooseFolder(): Promise<string | undefined> {
    const selected = await open({ directory: true, multiple: false });
    if (!selected) return;
    return Array.isArray(selected) ? selected[0] : selected;
  }

  async function pickAndSaveDir(key: DirKey) {
    const folder = await chooseFolder();
    if (!folder) return;

    if (key === "repository_dir") repoDraft.value = folder;
    if (key === "incoming_dir") incomingDraft.value = folder;

    await saveKey(key, folder);
  }

  // Setters for numbers (draft update + save)
  async function setNumber(key: NumberKey, v: number, immediate = true) {
    const value = Number(v);

    switch (key) {
      case "thumbnail_quality":
        thumbnailQualityDraft.value = value;
        break;
      case "thumbnail_width":
        thumbnailWidthDraft.value = value;
        break;
      case "thumbnail_height":
        thumbnailHeightDraft.value = value;
        break;
      case "ffprobe_timeout_s":
        ffprobeTimeoutDraft.value = value;
        break;
    }

    if (immediate) {
      await saveKey(key, value);
    } else {
      saveKeyDebounced(key, value);
    }
  }

  async function resetToDefaults(opts?: { includeNumbers?: boolean }) {
    // Always clear path overrides
    await saveKeys({
      repository_dir: null,
      incoming_dir: null,
      ...(opts?.includeNumbers
        ? {
            thumbnail_quality: DEFAULTS.thumbnail_quality,
            thumbnail_width: DEFAULTS.thumbnail_width,
            thumbnail_height: DEFAULTS.thumbnail_height,
            ffprobe_timeout_s: DEFAULTS.ffprobe_timeout_s,
          }
        : {}),
    });
  }

  return {
    // state
    effective,
    saving,
    lastSaveResult,
    query,

    // drafts
    repoDraft,
    incomingDraft,
    thumbnailQualityDraft,
    thumbnailWidthDraft,
    thumbnailHeightDraft,
    ffprobeTimeoutDraft,

    // actions
    pickAndSaveDir,
    setNumber,
    resetToDefaults,

    // escape hatches
    saveKey,
    saveKeys,
    saveKeyDebounced,
  };
}
