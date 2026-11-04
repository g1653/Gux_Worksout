const typeLabels: Record<string, { zh: string; en: string }> = {
  Run: { zh: '跑步', en: 'Run' },
  Ride: { zh: '骑行', en: 'Ride' },
  Hike: { zh: '徒步', en: 'Hike' },
  Swim: { zh: '游泳', en: 'Swim' },
  Workout: { zh: '综合训练', en: 'Workout' },
  Soccer: { zh: '足球', en: 'Soccer' },
  VirtualRide: { zh: '虚拟骑行', en: 'Virtual Ride' },
  'Trail Run': { zh: '越野跑', en: 'Trail Run' },
  TrailRun: { zh: '越野跑', en: 'Trail Run' },
  Training: { zh: '训练', en: 'Training' },
  WeightTraining: { zh: '力量训练', en: 'Weight Training' },
  StairStepper: { zh: '楼梯机', en: 'Stair Stepper' },
  WaterSport: { zh: '水上运动', en: 'Water Sport' },
  Flight: { zh: '飞行', en: 'Flight' },
  RoadTrip: { zh: '自驾', en: 'Road Trip' },
  Train: { zh: '铁路', en: 'Train' },
};
export const activityTypeLabel = (type: string, locale: string): string =>
  typeLabels[type]?.[locale === 'zh' ? 'zh' : 'en'] ?? type;

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
  const preferred = ['Run', 'Ride', 'Hike', 'Soccer', 'Workout'];
  const unique = [...new Set(types)];
  return [
    ...preferred.filter((type) => unique.includes(type)),
    ...unique.filter((type) => !preferred.includes(type)),
  ];
}
