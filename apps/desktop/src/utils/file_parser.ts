import { ModeEnum } from '../api/types';

export function parseModeFromPath(relPath: string): ModeEnum {
  const pathLower = relPath.toLowerCase();
  
  if (pathLower.includes('cont_rec')) {
    return ModeEnum.CONTINUOUS;
  } else if (pathLower.includes('evt_rec')) {
    return ModeEnum.EVENT;
  } else if (pathLower.includes('parking_rec')) {
    return ModeEnum.PARKING;
  } else if (pathLower.includes('manual_rec')) {
    return ModeEnum.MANUAL;
  } else if (pathLower.includes('sos_rec')) {
    return ModeEnum.SOS;
  } else {
    return ModeEnum.UNKNOWN;
  }
}

export function parseDateFromFilename(filename: string): Date | null {
  // Pattern: FRONT_20260113_080000.mp4
  const match = filename.match(/(\d{8})_\d{6}/);
  
  if (!match) return null;
  
  const dateStr = match[1]; // "20260113"
  const year = parseInt(dateStr.substring(0, 4));
  const month = parseInt(dateStr.substring(4, 6)) - 1; // JS months are 0-indexed
  const day = parseInt(dateStr.substring(6, 8));
  
  try {
    return new Date(year, month, day);
  } catch {
    return null;
  }
}

export function formatDateString(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}