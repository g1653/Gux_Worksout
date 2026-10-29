"""Persist administrative address fields, never infer provinces from street names."""

import json

PROVINCE_CODES = dict(
    zip(
        "BJ TJ HE SX NM LN JL HL SH JS ZJ AH FJ JX SD HA HB HN GD GX HI CQ SC GZ YN XZ SN GS QH NX XJ TW HK MO".split(),
        "北京市 天津市 河北省 山西省 内蒙古自治区 辽宁省 吉林省 黑龙江省 上海市 江苏省 浙江省 安徽省 福建省 江西省 山东省 河南省 湖北省 湖南省 广东省 广西壮族自治区 海南省 重庆市 四川省 贵州省 云南省 西藏自治区 陕西省 甘肃省 青海省 宁夏回族自治区 新疆维吾尔自治区 台湾省 香港特别行政区 澳门特别行政区".split(),
    )
)


def structured_location(location):
    if not location:
        return ""
    address = location.raw.get("address", {})
    code = address.get("country_code", "").lower()
    country = address.get("country", "")
    if not country:
        return ""
    province = address.get("state") or address.get("province") or ""
    admin_code = address.get("ISO3166-2-lvl4") or address.get("ISO3166-2-lvl3", "")
    if code == "cn" and admin_code.startswith("CN-"):
        province = PROVINCE_CODES.get(admin_code[3:], province)
    if code == "hk":
        province = "香港特别行政区"
    elif code == "mo":
        province = "澳门特别行政区"
    elif code == "tw":
        province = "台湾省"
    if code in {"cn", "hk", "mo", "tw"}:
        country = "中国"
    # Some Nominatim responses put municipalities in city rather than state.
    if code == "cn" and not province:
        for key in ("city", "municipality", "region"):
            value = address.get(key, "")
            if value in {
                "北京",
                "北京市",
                "天津",
                "天津市",
                "上海",
                "上海市",
                "重庆",
                "重庆市",
            }:
                province = value
                break
    return json.dumps(
        {
            "country": country,
            "country_code": code,
            "province": province,
            "city": address.get("city")
            or address.get("town")
            or address.get("county")
            or "",
            "source": "nominatim",
            "province_code": admin_code,
            "version": 1,
        },
        ensure_ascii=False,
    )


def needs_location(value):
    try:
        data = json.loads(value or "null")
        if not isinstance(data, dict) or data.get("version") != 1:
            return True
        if not data.get("country"):
            return True
        return data.get("country") == "中国" and not data.get("province")
    except (ValueError, TypeError):
        return True
