import type { Activity } from '../types';

// Calendar coverage, not daily mileage. Never divide a trip's distance by days.
export function roadTripDates(activity: Activity): string[] {
  if (activity.type !== 'RoadTrip' || !activity.end_date_local) return [];
  const start = activity.start_date_local.slice(0, 10);
  const end = activity.end_date_local.slice(0, 10);
  const from = Date.parse(`${start}T00:00:00Z`);
  const to = Date.parse(`${end}T00:00:00Z`);
  if (
    !Number.isFinite(from) ||
    !Number.isFinite(to) ||
    to < from ||
    to - from > 366 * 86400000
  )
    return [];
  return Array.from(
    { length: Math.round((to - from) / 86400000) + 1 },
    (_, i) => new Date(from + i * 86400000).toISOString().slice(0, 10)
  );
}
