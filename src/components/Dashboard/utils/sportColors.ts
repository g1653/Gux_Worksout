import type { Activity } from '../types';
import { isRunning, isCycling, isHiking } from './activityTypes';

export const sportPalettes: Record<string, string[]> = {
  Run: ['#fed7aa', '#fb923c', '#f97316', '#ea580c'],
  Ride: ['#bfdbfe', '#60a5fa', '#3b82f6', '#2563eb'],
  Hike: ['#bbf7d0', '#4ade80', '#22c55e', '#16a34a'],
  Swim: ['#cffafe', '#67e8f9', '#06b6d4', '#0891b2'],
  Soccer: ['#ede9fe', '#c4b5fd', '#8b5cf6', '#7c3aed'],
  Training: ['#fce7f3', '#f9a8d4', '#ec4899', '#db2777'],
};
export function sportGroup(type: string): string {
  if (isRunning(type)) return 'Run';
  if (isCycling(type)) return 'Ride';
  if (isHiking(type)) return 'Hike';
  if (type === 'Swim' || type === 'Soccer') return type;
  return 'Training';
}
export function sportDistances(activities: Activity[]) {
  return Object.keys(sportPalettes).flatMap((type) => {
    const items = activities.filter((a) => sportGroup(a.type) === type);
    return items.length
      ? [
          {
            type,
            distance: items.reduce(
              (sum, a) => sum + Math.max(0, a.distance),
              0
            ),
          },
        ]
      : [];
  });
}
const tripPalette = ['#fef3c7', '#fcd34d', '#f59e0b', '#d97706'];
export function segmentBackground(segments: { type: string; ratio: number }[]) {
  if (!segments.length) return 'var(--color-border)';
  const colors = segments.map(
    ({ type, ratio }) =>
      (type === 'RoadTrip' ? tripPalette : sportPalettes[type])[
        Math.max(0, Math.ceil(Math.min(ratio, 1) * 4) - 1)
      ]
  );
  if (colors.length === 1) return colors[0];
  return (
    'linear-gradient(to bottom, ' +
    colors
      .map(
        (color, i) =>
          color +
          ' ' +
          (i * 100) / colors.length +
          '% ' +
          ((i + 1) * 100) / colors.length +
          '%'
      )
      .join(', ') +
    ')'
  );
}
