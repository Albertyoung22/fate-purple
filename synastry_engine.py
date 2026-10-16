# -*- coding: utf-8 -*-
"""
雙人命盤合婚與因果合盤契合度運算核心 (Destiny Synastry & Compatibility Engine)
結合子平八字五行生剋、干支六合三合、納音互補、紫微宮位共振與宿世因緣分析。
"""

from datetime import datetime
from lunar_python import Solar

try:
    from app import to_traditional
except:
    def to_traditional(x): return x

# 五行相生相剋
WU_XING_RELATION = {
    ("木", "火"): ("生", "相生互旺，如沐春風"),
    ("火", "土"): ("生", "相生相融，溫暖厚實"),
    ("土", "金"): ("生", "相生聚財，穩固開展"),
    ("金", "水"): ("生", "相生靈動，相互啟發"),
    ("水", "木"): ("生", "相生滋養，甘苦與共"),
    ("木", "木"): ("和", "比和共振，攜手並進"),
    ("火", "火"): ("和", "比和熱情，聲勢浩大"),
    ("土", "土"): ("和", "比和踏實，信任深厚"),
    ("金", "金"): ("和", "比和剛強，需互讓步"),
    ("水", "水"): ("和", "比和流暢，默契十足"),
    ("水", "火"): ("剋", "水火相激，熱烈中防口角"),
    ("火", "金"): ("剋", "火煉秋金，考驗彼此耐心"),
    ("金", "木"): ("剋", "金克枯木，直言易生摩擦"),
    ("木", "土"): ("剋", "木破實土，控制慾需放鬆"),
    ("土", "水"): ("剋", "土掩流水，需多坦誠溝通")
}

# 天干五合
TIAN_GAN_HE = {
    ("甲", "己"): "中正之合 · 寬厚仁慈",
    ("己", "甲"): "中正之合 · 寬厚仁慈",
    ("乙", "庚"): "仁義之合 · 剛柔並濟",
    ("庚", "乙"): "仁義之合 · 剛柔並濟",
    ("丙", "辛"): "威制之合 · 儀表端莊",
    ("辛", "丙"): "威制之合 · 儀表端莊",
    ("丁", "壬"): "淫匿之合 · 感情深厚",
    ("壬", "丁"): "淫匿之合 · 感情深厚",
    ("戊", "癸"): "無情之合 · 相敬如賓",
    ("癸", "戊"): "無情之合 · 相敬如賓"
}

# 地支六合
DI_ZHI_HE = {
    ("子", "丑"): "合化土 · 互補默契",
    ("丑", "子"): "合化土 · 互補默契",
    ("寅", "亥"): "合化木 · 志同道合",
    ("亥", "寅"): "合化木 · 志同道合",
    ("卯", "戌"): "合化火 · 溫暖長久",
    ("戌", "卯"): "合化火 · 溫暖長久",
    ("辰", "酉"): "合化金 · 彼此成就",
    ("酉", "辰"): "合化金 · 彼此成就",
    ("巳", "申"): "合化水 · 靈活多變",
    ("申", "巳"): "合化水 · 靈活多變",
    ("午", "未"): "合化土 · 圓融和樂",
    ("未", "午"): "合化土 · 圓融和樂"
}

# 地支六沖
DI_ZHI_CHONG = {
    ("子", "午"): "水火激盪，性格反差大",
    ("丑", "未"): "土氣互衝，各有堅持防執著",
    ("寅", "申"): "金木交戰，各奔前程聚少離多",
    ("卯", "酉"): "情意搖擺，易因第三者或雜音起疑",
    ("辰", "戌"): "庫位對沖，理財與生活觀念需磨合",
    ("巳", "亥"): "心性游移，喜好變動需建立安全感"
}

def analyze_compatibility(person1, person2, relation_type="情侶合婚"):
    """
    計算雙人命理合盤契合度
    person1, person2: dict(name, birth_date, birth_hour, gender)
    """
    p1_name = person1.get("name", "緣主甲")
    p2_name = person2.get("name", "緣主乙")
    
    # 預設基準分 60 分
    score = 60
    bonuses = []
    cautions = []
    
    # 提取出生四柱
    def get_eight_char(p_dict):
        try:
            b_str = p_dict.get("birth_date", "1990-01-01")
            parts = [int(x) for x in b_str.split('-')]
            h_val = p_dict.get("birth_hour", 0)
            hour = 0
            if isinstance(h_val, int):
                hour = (h_val % 12) * 2
            elif str(h_val).isdigit():
                hour = (int(h_val) % 12) * 2
            solar = Solar.fromYmdHms(parts[0], parts[1], parts[2], hour, 0, 0)
            return solar.getLunar().getEightChar()
        except:
            solar = Solar.fromYmdHms(1990, 1, 1, 0, 0, 0)
            return solar.getLunar().getEightChar()

    ec1 = get_eight_char(person1)
    ec2 = get_eight_char(person2)
    
    # 1. 日主天干生剋 (命格核心)
    day_gan1 = ec1.getDayGan()
    day_gan2 = ec2.getDayGan()
    
    gan_element = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
    elem1 = gan_element.get(day_gan1, "土")
    elem2 = gan_element.get(day_gan2, "土")
    
    # 檢查天干五合
    if (day_gan1, day_gan2) in TIAN_GAN_HE:
        he_desc = TIAN_GAN_HE[(day_gan1, day_gan2)]
        score += 15
        bonuses.append(f"日柱天干現【{day_gan1}{day_gan2}{he_desc}】：靈魂深度吸引，天生自帶強烈默契。")
    else:
        rel_type, rel_desc = WU_XING_RELATION.get((elem1, elem2), ("和", "平順"))
        if rel_type == "生":
            score += 12
            bonuses.append(f"日元五行【{elem1}與{elem2}相生】：{rel_desc}，相處能激勵彼此成長。")
        elif rel_type == "和":
            score += 8
            bonuses.append(f"日元五行【{elem1}見{elem2}同旺】：志趣相投，像知己般自在親切。")
        else:
            score -= 5
            cautions.append(f"日元五行【{elem1}與{elem2}相剋】：{rel_desc}，溝通需多站在對方立場設想。")

    # 2. 地支合沖 (夫妻宮合化 - 日支)
    day_zhi1 = ec1.getDayZhi()
    day_zhi2 = ec2.getDayZhi()
    
    if (day_zhi1, day_zhi2) in DI_ZHI_HE:
        he_desc = DI_ZHI_HE[(day_zhi1, day_zhi2)]
        score += 16
        bonuses.append(f"夫妻宮地支成【{day_zhi1}{day_zhi2}六合】：{he_desc}，生活起居與內在價值觀高度和諧。")
    elif (day_zhi1, day_zhi2) in DI_ZHI_CHONG or (day_zhi2, day_zhi1) in DI_ZHI_CHONG:
        chong_desc = DI_ZHI_CHONG.get((day_zhi1, day_zhi2)) or DI_ZHI_CHONG.get((day_zhi2, day_zhi1))
        score -= 10
        cautions.append(f"夫妻宮地支現【{day_zhi1}{day_zhi2}相沖】：{chong_desc}，宜彼此保留個人空間，切莫翻舊帳。")
    else:
        score += 5
        bonuses.append("夫妻宮地支氣場平穩無沖煞，能經得起柴米油鹽之歲月考驗。")

    # 3. 生肖生剋 (年支)
    year_zhi1 = ec1.getYearZhi()
    year_zhi2 = ec2.getYearZhi()
    if (year_zhi1, year_zhi2) in DI_ZHI_HE:
        score += 10
        bonuses.append(f"年生肖得六合暗助：長輩緣與外在社會人脈相互扶持加分。")
    elif (year_zhi1, year_zhi2) in DI_ZHI_CHONG or (year_zhi2, year_zhi1) in DI_ZHI_CHONG:
        score -= 6
        cautions.append(f"年生肖帶沖：家庭或生長環境背景略有差異，需尊重各自生活習性。")

    # 4. 五行納音互補
    nayin1 = ec1.getDayNaYin()
    nayin2 = ec2.getDayNaYin()
    bonuses.append(f"納音五行共振：{p1_name}為【{nayin1}】，{p2_name}為【{nayin2}】，磁場相互映照調候。")

    # 總分限制 45 ~ 98
    final_score = max(45, min(98, score))
    
    if final_score >= 88:
        destiny_title = "天作之合 · 宿世良緣"
        stars = "★★★★★"
        advice = "你們前世定有深厚善緣，今生相遇自帶引力。請珍惜這份難得的因緣，相互扶持可興旺彼此家道。"
    elif final_score >= 76:
        destiny_title = "志趣相投 · 珠聯璧合"
        stars = "★★★★☆"
        advice = "彼此優缺點互補性極高，多在重大決策上相互商量，將是彼此事業與人生最強大的神隊友。"
    elif final_score >= 65:
        destiny_title = "歡喜冤家 · 平淡是福"
        stars = "★★★☆☆"
        advice = "偶有生活習慣小摩擦，吵過後反而更了解彼此。只要不踩對方核心底線，日子將越過越踏實。"
    else:
        destiny_title = "磨練道場 · 化怨為祥"
        stars = "★★☆☆☆"
        advice = "雙方性格均極具主見，相處宜退一步海闊天空。多肯定對方的付出，少些挑剔要求，方可共渡風雨。"

    return to_traditional({
        "p1_name": p1_name,
        "p2_name": p2_name,
        "relation_type": relation_type,
        "score": final_score,
        "stars": stars,
        "destiny_title": destiny_title,
        "advice": advice,
        "p1_details": f"日主【{day_gan1}{elem1}】· 納音【{nayin1}】",
        "p2_details": f"日主【{day_gan2}{elem2}】· 納音【{nayin2}】",
        "bonuses": bonuses,
        "cautions": cautions if cautions else ["目前兩造命盤無重大沖刑，只需平常心坦誠相待。"]
    })
