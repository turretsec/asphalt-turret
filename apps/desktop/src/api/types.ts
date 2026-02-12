export interface Clip {
  id: number;
  file_hash: string;
  repo_path: string;
  original_filename: string | null;
  camera: CameraEnum;
  mode: ModeEnum;
  recorded_at: string | null;
  duration_s: number | null;
  size_bytes: number | null;
  codec: string | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  imported_at: string;
  probe_version: number | null;
  probed_at: string | null;
  metadata_status: MetadataStatusEnum;
  metadata_error: string | null;
  metadata_json: string | null;
}

export enum MetadataStatusEnum {
  PENDING = "pending",
  EXTRACTED = "extracted",
  FAILED = "failed",
  PARTIAL = "partial",
}

export interface Volume {
  drive_root: string;
  volume_label: string;
  volume_uid: string;
  is_removable: boolean;
}

export enum SDFileImportState {
  NEW = "new",
  PENDING = "pending",
  IMPORTED = "imported",
  FAILED = "failed",
}

export interface SDCard {
  volume_uid: string;
  volume_label: string | null;
  first_seen_at: string;
  last_seen_at: string;
  is_connected: boolean;
  drive_root: string | null;
  total_files: number;
  pending_files: number;
}

export interface SDCardsListResponse {
  cards: SDCard[];
  connected_count: number;
}

export interface SDCardDetail extends SDCard {
  imported_files: number;
  failed_files: number;
}

export interface SDFile {
  id: number;
  rel_path: string;
  size_bytes: number;
  mtime: string;
  import_state: SDFileImportState;
  fingerprint: string;
  last_seen_at: string;
}

export interface SDFilesListResponse {
  volume_uid: string;
  volume_label: string | null;
  total_files: number;
  returned_files: number;
  files: SDFile[];
}

export type PlayableMedia =
  | { type: 'clip'; data: Clip }
  | { type: 'sd_file'; data: SDFile; volume_uid: string };

export enum ModeEnum {
  CONTINUOUS = "continuous",
  EVENT = "event",
  PARKING = "parking",
  MANUAL = "manual",
  SOS = "sos",
  UNKNOWN = "unknown"
}

export type DatePreset = 'all' | 'today' | 'yesterday' | '7d' | 'custom';

export type ImportFilters = {
  modes: ModeEnum[];
  states: SDFileImportState[];
  datePreset: DatePreset;
  dateRange: [Date, Date] | null;
}

export interface ImportRequest {
  volume_uid: string;
  file_ids: number[];
}

export interface ImportResponse {
  job_id: number;
  total_files: number;
  message: string;
}

export enum CameraEnum {
  FRONT = "front",
  REAR = "rear",
  UNKNOWN = "unknown"
}



export interface DeleteClipsRequest {
  clip_ids: number[];
}

export interface DeleteClipsResponse {
  deleted_count: number;
  failed_count: number;
  message: string;
}

export interface ExportClipsRequest {
  clip_ids: number[];
  destination_dir: string;
}

export interface ExportClipsResponse {
  exported_count: number;
  failed_count: number;
  message: string;
  destination: string;
}

// export type SettingsResponse = {
//   user: Record<string, any>;
//   effective: Record<string, any>;
//   restart_required?: boolean;
//   changed_keys?: string[];
// };

// Settings types matching backend
export interface UserSettings {
  version: number;
  thumbnail_width: number | null;
  thumbnail_height: number | null;
  thumbnail_quality: number | null;
  ffprobe_timeout_s: number | null;
  repository_dir: string | null;
  incoming_dir: string | null;
}

export interface EffectiveSettings {
  base_dir: string;
  database_url: string;
  ffprobe_timeout_s: number;
  thumbnail_width: number;
  thumbnail_height: number;
  thumbnail_quality: number;
  repository_dir: string;
  incoming_dir: string;
  thumbnails_dir: string;
  ffprobe_path: string;
  ffmpeg_path: string;
}

export interface SettingsResponse {
  changed_keys?: string[];
  restart_required?: boolean;
  user: UserSettings;
  effective: EffectiveSettings;
}

export enum JobState {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum JobType {
  IMPORT_BATCH = 'import_batch',
  PROBE_BATCH = 'probe_batch',
  PROBE_CLIP = 'probe_clip',
}

export interface JobStatus {
  job_id: number;
  type: JobType;
  state: JobState;
  progress: number;
  total: number | null;
  completed: number | null;
  failed: number | null;
  message: string | null;
  created_at: string;
  updated_at: string;
}