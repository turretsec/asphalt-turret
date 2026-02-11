export interface Clip {
  id: number;
  file_hash: string;
  original_filename: string;
  imported_at: string;
  recorded_at: string;
  camera: CameraEnum;
  mode: ModeEnum;
  repo_path: string;
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