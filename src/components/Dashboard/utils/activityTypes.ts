const typeLabels: Record<string, string> = {
  VirtualRide: '虚拟骑行',
  'Trail Run': '越野跑',
  TrailRun: '越野跑',
};
export const activityTypeLabel = (type: string): string =>
  typeLabels[type] ?? type;

export const isRunning = (type: string): boolean =>
  ['run', 'running', 'trailrun', 'virtualrun'].includes(
    type.replace(/[\s_-]/g, '').toLowerCase()
  );

export const isHiking = (type: string): boolean =>
  ['hike', 'hiking'].includes(type.replace(/[\s_-]/g, '').toLowerCase());

export const isCycling = (type: string): boolean =>
  [
    'ride',
    'virtualride',
    'mountainbikeride',
    'gravelride',
    'ebikeride',
    'emountainbikeride',
  ].includes(type.replace(/[\s_-]/g, '').toLowerCase());

export function orderActivityTypes(types: string[]): string[] {
  const preferred = ['Run', 'Ride', 'Hike', 'Workout'];
  const unique = [...new Set(types)];
  return [
    ...preferred.filter((type) => unique.includes(type)),
    ...unique.filter((type) => !preferred.includes(type)),
  ];
}
