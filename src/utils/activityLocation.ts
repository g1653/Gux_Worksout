const provinces = [
  '北京市',
  '天津市',
  '上海市',
  '重庆市',
  '河北省',
  '山西省',
  '辽宁省',
  '吉林省',
  '黑龙江省',
  '江苏省',
  '浙江省',
  '安徽省',
  '福建省',
  '江西省',
  '山东省',
  '河南省',
  '湖北省',
  '湖南省',
  '广东省',
  '海南省',
  '四川省',
  '贵州省',
  '云南省',
  '陕西省',
  '甘肃省',
  '青海省',
  '内蒙古自治区',
  '广西壮族自治区',
  '西藏自治区',
  '宁夏回族自治区',
  '新疆维吾尔自治区',
  '香港特别行政区',
  '澳门特别行政区',
  '台湾省',
];

function canonicalProvince(value: string): string | null {
  const normalized = value.replace(/臺/g, '台').replace(/澳門/g, '澳门');
  return (
    provinces.find(
      (p) =>
        p === normalized ||
        p.replace(
          /(?:壮族自治区|回族自治区|维吾尔自治区|自治区|特别行政区|省|市)$/,
          ''
        ) === normalized
    ) ?? null
  );
}

export function parseActivityLocation(value: string | null | undefined): {
  country: string;
  province: string;
  city: string;
} | null {
  if (!value?.trim().startsWith('{')) return null;
  try {
    let data;
    try {
      data = JSON.parse(value);
    } catch {
      data = JSON.parse(value.replace(/'/g, '"').replace(/\bNone\b/g, 'null'));
    }
    if (!data || typeof data !== 'object') return null;
    const country = typeof data.country === 'string' ? data.country : '';
    const chinese = ['中国', '中國', 'China', '中华人民共和国'].includes(
      country
    );
    return {
      country: chinese ? '中国' : country,
      province:
        chinese && typeof data.province === 'string'
          ? (canonicalProvince(data.province) ?? '')
          : '',
      city: typeof data.city === 'string' ? data.city : '',
    };
  } catch {
    return null;
  }
}

export function extractProvince(
  value: string | null | undefined
): string | null {
  if (!value) return null;
  if (value.trim().startsWith('{'))
    return parseActivityLocation(value)?.province || null;
  const parts = value
    .split(/[,，]/)
    .map((part) => part.trim())
    .filter(Boolean);
  // Legacy display addresses are ordered street → province → country.
  // Exact components prevent 河北路 in 北京市 from becoming 河北省.
  const country = parts.at(-1);
  if (
    parts.length > 1 &&
    !['中国', '中國', 'China', '中华人民共和国'].includes(country ?? '')
  )
    return null;
  for (const part of [...parts].reverse()) {
    const province = canonicalProvince(part);
    if (province) return province;
  }
  return null;
}
