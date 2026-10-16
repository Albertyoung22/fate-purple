# -*- coding: utf-8 -*-
"""
動態流年與十二流月吉凶波動雷達核心 (Flow Year & Monthly Fortune Radar Engine)
支援指定任意公曆年份（如 2024、2025、2026、2027...），
精準推導流年干支、正統十天干四化、五虎遁起十二流月干支，並合參緣主紫微宮位與生辰種子。
"""

import random
from datetime import datetime

try:
    from app import to_traditional
except Exception:
    def to_traditional(x): return x

GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZODIAC = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]

# 五虎遁起月天干首位對照表 (正月建寅)
WUHUDUN_MAP = {
    "甲": "丙", "己": "丙",
    "乙": "戊", "庚": "戊",
    "丙": "庚", "辛": "庚",
    "丁": "壬", "壬": "壬",
    "戊": "甲", "癸": "甲"
}

# 正統紫微十天干四化星曜與效應
SIHUA_TABLE = {
    "甲": [
        {"star": "廉貞", "trans": "化祿", "effect": "官祿名譽生輝，事業公關大吉，商務偏財顯現"},
        {"star": "破軍", "trans": "化權", "effect": "大刀闊斧變革，開創新局，敢破敢立掌握實權"},
        {"star": "武曲", "trans": "化科", "effect": "理財精算獲利，專業技能獲業界肯定與認證"},
        {"star": "太陽", "trans": "化忌", "effect": "慎防面子逞強、男性長輩健康波折與合夥是非"}
    ],
    "乙": [
        {"star": "天機", "trans": "化祿", "effect": "智謀生財，靈動變通，企劃推廣迎來豐厚收益"},
        {"star": "天梁", "trans": "化權", "effect": "貴人長輩扶持，專業權威穩固，化險為夷逢凶化吉"},
        {"star": "紫微", "trans": "化科", "effect": "領導威望日隆，名聲遠播，易獲官方或組織表彰"},
        {"star": "太陰", "trans": "化忌", "effect": "情緒起伏焦慮，防範暗疾、不動產合約漏失與女性是非"}
    ],
    "丙": [
        {"star": "天同", "trans": "化祿", "effect": "福星高照，生活安樂，人際圓融，以和生財"},
        {"star": "天機", "trans": "化權", "effect": "謀略深遠，思維敏銳，主動出擊掌握事業主導權"},
        {"star": "文昌", "trans": "化科", "effect": "考運官名亨通，文書合約多得助力，品牌聲譽鵲起"},
        {"star": "廉貞", "trans": "化忌", "effect": "慎防合約隱患、法律官司、感情糾纏與血光偏門風險"}
    ],
    "丁": [
        {"star": "太陰", "trans": "化祿", "effect": "財庫豐厚，置產順遂，女性貴人相助，暗財滋養"},
        {"star": "天同", "trans": "化權", "effect": "主動創造福分，安樂中求突破，執行力與競爭力增強"},
        {"star": "天機", "trans": "化科", "effect": "策劃創意獲獎，聲譽通達，適合深造進修與傳播諮詢"},
        {"star": "巨門", "trans": "化忌", "effect": "慎防口舌是非、小人暗箭、溝通誤會與合約口角"}
    ],
    "戊": [
        {"star": "貪狼", "trans": "化祿", "effect": "應酬人脈開花，商業偏財大發，才藝與社交魅力四射"},
        {"star": "太陰", "trans": "化權", "effect": "資產掌控得宜，財務實權在手，利於女性與不動產投資"},
        {"star": "右弼", "trans": "化科", "effect": "同輩夥伴相助，貴人暗中相挺，公關聲量大增"},
        {"star": "天機", "trans": "化忌", "effect": "易鑽牛角尖，決策瞻前顧後失良機，交通出行宜謹慎"}
    ],
    "己": [
        {"star": "武曲", "trans": "化祿", "effect": "正財滾滾，實幹致富，金融操作與實體經商大展宏圖"},
        {"star": "貪狼", "trans": "化權", "effect": "野心勃勃拓展版圖，掌控力與開疆拓土能量極強"},
        {"star": "天梁", "trans": "化科", "effect": "醫藥文教養生揚名，長輩提攜，清譽與口碑遠揚"},
        {"star": "文曲", "trans": "化忌", "effect": "慎防票據契約漏洞、口舌詐欺、情場失意與金錢借貸糾紛"}
    ],
    "庚": [
        {"star": "太陽", "trans": "化祿", "effect": "聲名顯赫，貴氣逼人，光明磊落廣結人脈大開財路"},
        {"star": "武曲", "trans": "化權", "effect": "果決強勢，鐵腕理財，資金調度果斷，開拓大市場"},
        {"star": "太陰", "trans": "化科", "effect": "內斂智慧獲讚賞，理財投資細膩穩健，母系家族助力大"},
        {"star": "天同", "trans": "化忌", "effect": "情緒慵懶消極，人際相處易生悶氣，享樂過度致財氣外流"}
    ],
    "辛": [
        {"star": "巨門", "trans": "化祿", "effect": "以口生財，名嘴行銷，談判說服無往不利，財路大開"},
        {"star": "太陽", "trans": "化權", "effect": "名揚四海，地位躍升，大權在握，宜展現領導魄力"},
        {"star": "文曲", "trans": "化科", "effect": "才華橫溢，文藝學術深獲好評，名聲廣泛傳播"},
        {"star": "文昌", "trans": "化忌", "effect": "慎防文書契約失誤、支票信用瑕疵、考試失常與文書糾紛"}
    ],
    "壬": [
        {"star": "天梁", "trans": "化祿", "effect": "祖上蔭庇，意外贈與，長輩福報連連，投機不如長線守成"},
        {"star": "紫微", "trans": "化權", "effect": "尊貴威嚴，登高一呼萬山應，自主創業或掌權大展拳腳"},
        {"star": "左輔", "trans": "化科", "effect": "得力助手相輔，外部贊助與合夥聲譽佳，推廣水到渠成"},
        {"star": "武曲", "trans": "化忌", "effect": "資金鏈吃緊，短線投資易受挫，切莫為人作保或過度擴張"}
    ],
    "癸": [
        {"star": "破軍", "trans": "化祿", "effect": "破舊立新大發財，跨界轉型成功，意外機緣帶來暴利"},
        {"star": "巨門", "trans": "化權", "effect": "言辭犀利震懾四方，法務辯論與公關談判威信倍增"},
        {"star": "太陰", "trans": "化科", "effect": "美學不動產獲利，女性貴人指引迷津，名聲溫潤優雅"},
        {"star": "貪狼", "trans": "化忌", "effect": "慎防貪慾過熾受騙、酒色桃花惹禍與投機失利陷泥淖"}
    ]
}

# 十二月月令地支主題與自然氣象
MONTH_THEMES = [
    {"zhi": "寅", "name": "正月(寅月)", "theme": "開春立志 · 驛馬啟動", "base": (74, 78, 70, 75)},
    {"zhi": "卯", "name": "二月(卯月)", "theme": "草木萌發 · 智慧通達", "base": (76, 84, 79, 80)},
    {"zhi": "辰", "name": "三月(辰月)", "theme": "辰庫納水 · 財氣湧現", "base": (86, 82, 75, 78)},
    {"zhi": "巳", "name": "四月(巳月)", "theme": "初夏向陽 · 多勞多得", "base": (80, 81, 73, 72)},
    {"zhi": "午", "name": "五月(午月)", "theme": "盛夏至陽 · 宜靜沉潛", "base": (68, 70, 65, 62)},
    {"zhi": "未", "name": "六月(未月)", "theme": "土庫生金 · 貴人相迎", "base": (85, 87, 86, 82)},
    {"zhi": "申", "name": "七月(申月)", "theme": "金氣蕭蕭 · 拓展慎合", "base": (75, 76, 70, 70)},
    {"zhi": "酉", "name": "八月(酉月)", "theme": "仲秋明月 · 桃花相映", "base": (78, 80, 90, 76)},
    {"zhi": "戌", "name": "九月(戌月)", "theme": "火庫聚勢 · 氣勢登峰", "base": (92, 90, 84, 83)},
    {"zhi": "亥", "name": "十月(亥月)", "theme": "初冬涵養 · 沉澱謀新", "base": (82, 85, 77, 80)},
    {"zhi": "子", "name": "十一月(子月)", "theme": "深冬嚴藏 · 避險守成", "base": (62, 65, 58, 60)},
    {"zhi": "丑", "name": "十二月(丑月)", "theme": "歲末結總 · 大局底定", "base": (85, 87, 82, 85)},
]

# 六合與對沖對照
CHONG_MAP = {"子": "午", "丑": "未", "寅": "申", "卯": "酉", "辰": "戌", "巳": "亥",
             "午": "子", "未": "丑", "申": "寅", "酉": "卯", "戌": "辰", "亥": "巳"}
HE_MAP = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
          "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}

def calculate_flow_year_radar(user_info=None):
    """
    動態計算指定年份（target_year，如 2024、2025、2026、2027...）
    之流年干支、四化吉凶與 1~12 月財富、事業、感情、健康波動雷達
    """
    user_info = user_info or {}
    b_date = str(user_info.get("birth_date", "1990-01-01"))
    b_hour = int(user_info.get("birth_hour", 0) or 0)
    
    # 支援指定年份，預設為傳入的 target_year / year 或當前年份
    raw_year = user_info.get("target_year") or user_info.get("year")
    try:
        target_year = int(raw_year) if raw_year else datetime.now().year
    except (ValueError, TypeError):
        target_year = datetime.now().year
        
    if target_year < 1920 or target_year > 2100:
        target_year = 2026

    # 1. 流年干支推算
    gan_idx = (target_year - 4) % 10
    zhi_idx = (target_year - 4) % 12
    year_gan = GAN[gan_idx]
    year_zhi = ZHI[zhi_idx]
    year_zodiac = ZODIAC[zhi_idx]
    
    # 雅稱五行特色
    zodiac_titles = {
        "子": "靈鼠", "丑": "金牛", "寅": "青虎", "卯": "玉兔",
        "辰": "蒼龍", "巳": "靈蛇", "午": "赤馬", "未": "白羊",
        "申": "神猴", "酉": "彩鳳", "戌": "靈犬", "亥": "富豬"
    }
    zodiac_title = zodiac_titles.get(year_zhi, year_zodiac)
    year_ganzhi_str = f"歲次{year_gan}{year_zhi}{zodiac_title}年"

    # 2. 流年四化星曜
    four_transforms = SIHUA_TABLE.get(year_gan, SIHUA_TABLE["丙"])

    # 3. 五虎遁起十二流月干支
    first_month_gan = WUHUDUN_MAP.get(year_gan, "丙")
    first_month_gan_idx = GAN.index(first_month_gan)

    # 依生辰與指定年份生成確定性種子，確保每位緣主每年的運勢唯一且連貫
    seed_val = sum(ord(c) for c in b_date) + b_hour * 13 + target_year * 37
    rng = random.Random(seed_val)

    monthly_series = []
    overall_list = []

    for idx, item in enumerate(MONTH_THEMES):
        m_num = idx + 1
        m_gan = GAN[(first_month_gan_idx + idx) % 10]
        m_zhi = item["zhi"]
        m_ganzhi = f"{m_gan}{m_zhi}月"
        
        # 公曆預估對應年月 (正月約落在 2 月)
        solar_cal_m = (m_num % 12) + 1
        solar_cal_y = target_year if m_num < 12 else target_year + 1
        solar_str = f"{solar_cal_y}/{solar_cal_m:02d}"

        # 地支生剋調適 (流月逢太歲相沖、相合或本命影響)
        base_w, base_c, base_l, base_h = item["base"]
        
        if m_zhi == CHONG_MAP.get(year_zhi):
            # 歲破/月破對沖，動盪守成
            theme_suffix = " · 逢歲沖宜謹慎避險"
            base_w -= 12; base_c -= 10; base_l -= 12; base_h -= 10
        elif m_zhi == HE_MAP.get(year_zhi):
            # 歲君六合，貴人相迎
            theme_suffix = " · 歲合貴人化難呈祥"
            base_w += 8; base_c += 8; base_l += 9; base_h += 6
        elif m_zhi == year_zhi:
            # 歲星坐月(伏吟)，多思宜定
            theme_suffix = " · 伏吟當值修煉內功"
            base_w -= 5; base_c -= 4; base_l -= 6; base_h -= 7
        else:
            theme_suffix = ""

        # 個人微調 (-6 ~ +8)
        offset_w = rng.randint(-6, 8)
        offset_c = rng.randint(-6, 8)
        offset_l = rng.randint(-6, 8)
        offset_h = rng.randint(-6, 6)

        w_score = max(42, min(99, base_w + offset_w))
        c_score = max(42, min(99, base_c + offset_c))
        l_score = max(42, min(99, base_l + offset_l))
        h_score = max(42, min(99, base_h + offset_h))
        overall = int(w_score * 0.35 + c_score * 0.35 + l_score * 0.15 + h_score * 0.15)
        overall_list.append(overall)

        monthly_series.append({
            "month": m_num,
            "name": f"{m_num}月 ({m_ganzhi})",
            "ganzhi": m_ganzhi,
            "solar": solar_str,
            "theme": f"{item['theme']}{theme_suffix}",
            "wealth": w_score,
            "career": c_score,
            "love": l_score,
            "health": h_score,
            "overall": overall
        })

    # 尋找年度最強巔峰月與守成避險月
    peak_idx = overall_list.index(max(overall_list))
    caution_idx = overall_list.index(min(overall_list))
    peak_month = monthly_series[peak_idx]
    caution_month = monthly_series[caution_idx]

    # 年度宏觀總結
    lu_star = [x["star"] for x in four_transforms if x["trans"] == "化祿"][0]
    ji_star = [x["star"] for x in four_transforms if x["trans"] == "化忌"][0]
    summary_text = (
        f"{target_year} {year_ganzhi_str}，由「{lu_star}化祿」掌管年度氣場生發機遇，利於積極開拓拓寬版圖；"
        f"同時須留心「{ji_star}化忌」之因果考驗，在關鍵合約與財務邊界上黑白分明。"
        f"全年在第 {peak_month['month']} 月迎來年度氣數頂峰，第 {caution_month['month']} 月宜放緩腳步守成蓄力。"
    )

    result = {
        "year": target_year,
        "year_ganzhi": year_ganzhi_str,
        "four_transforms": four_transforms,
        "summary": summary_text,
        "peak_month": {
            "month": peak_month["month"],
            "name": peak_month["name"],
            "score": peak_month["overall"],
            "theme": peak_month["theme"],
            "advice": f"此月為 {target_year} 年度氣數最強頂峰，無論開拓事業、大額投資、求婚或重要談判均宜主動推進！"
        },
        "caution_month": {
            "month": caution_month["month"],
            "name": caution_month["name"],
            "score": caution_month["overall"],
            "theme": caution_month["theme"],
            "advice": f"此月氣場波動較大，切忌大額借貸、衝動冒進或無謂口角爭執，宜沉著守成修身養性。"
        },
        "monthly_data": monthly_series
    }
    return to_traditional(result)
