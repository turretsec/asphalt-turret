import type { DatePreset } from '../api/types';

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function endOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}

/**
 * Returns true if `date` falls within the window described by `preset`
 * (and optionally a custom `range`).
 *
 * Returns false if `date` is null — callers can decide how to handle
 * items with no date (typically show them or always include them).
 */
export function inDateWindow(
  date: Date | null,
  preset: DatePreset,
  range: [Date, Date] | null,
): boolean {
  if (!date) return false;

  const now = new Date();
  const todayStart = startOfDay(now);

  switch (preset) {
    case 'all':
      return true;

    case 'today':
      return date >= todayStart && date <= endOfDay(now);

    case 'yesterday': {
      const y = new Date(todayStart);
      y.setDate(y.getDate() - 1);
      return date >= y && date <= endOfDay(y);
    }

    case '7d': {
      const start = new Date(todayStart);
      start.setDate(start.getDate() - 6);
      return date >= start && date <= endOfDay(now);
    }

    case 'custom':
      if (!range) return true;
      return date >= startOfDay(range[0]) && date <= endOfDay(range[1]);

    default:
      return true;
  }
}