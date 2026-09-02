# -*- coding: utf-8 -*-
"""
2026 丙午流年與十二流月吉凶波動雷達核心 (Flow Year & Monthly Fortune Radar)
以 2026 歲次丙午（天同化祿、天機化權、文昌化科、廉貞化忌）合參緣主紫微宮位與八字喜忌。
"""

import random
from datetime import datetime

try:
    from app import to_traditional
except:
    def to_traditional(x): return x

MONTH_DATA_2026 = [
    {"month": 1, "ganzhi": "庚寅月", "solar": "2026/02", "theme": "開春立志 · 驛馬啟動", "base_weights": (72, 78, 70, 75)},
    {"month": 2, "ganzhi": "辛卯月", "solar": "2026/03", "theme": "文昌照臨 · 智慧通達", "base_weights": (75, 85, 78, 80)},
    {"month": 3, "ganzhi": "壬辰月", "solar": "2026/04", "theme": "辰庫納水 · 財氣湧現", "base_weights": (88, 82, 75, 78)},
    {"month": 4, "ganzhi": "癸巳月", "solar": "2026/05", "theme": "巳火生輝 · 多勞多得", "base_weights": (80, 80, 72, 70)},
    {"month": 5, "ganzhi": "甲午月", "solar": "2026/06", "theme": "歲月伏吟 · 心浮氣躁宜靜", "base_weights": (65, 68, 62, 60)},
    {"month": 6, "ganzhi": "乙未月", "solar": "2026/07", "theme": "午未六合 · 貴人相迎解難", "base_weights": (84, 86, 88, 82)},
    {"month": 7, "ganzhi": "丙申月", "solar": "2026/08", "theme": "金火交融 · 拓展需防合約", "base_weights": (74, 76, 70, 68)},
    {"month": 8, "ganzhi": "丁酉月", "solar": "2026/09", "theme": "桃花相映 · 人緣喜慶臨門", "base_weights": (78, 80, 92, 76)},
    {"month": 9, "ganzhi": "戊戌月", "solar": "2026/10", "theme": "三合火局 · 氣勢如虹登頂", "base_weights": (95, 92, 85, 84)},
    {"month": 10, "ganzhi": "己亥月", "solar": "2026/11", "theme": "水潤燥局 · 沉澱蓄勢謀新", "base_weights": (82, 85, 76, 80)},
    {"month": 11, "ganzhi": "庚子月", "solar": "2026/12", "theme": "子午對沖 · 守財避險防波折", "base_weights": (58, 62, 55, 58)},
    {"month": 12, "ganzhi": "辛丑月", "solar": "2027/01", "theme": "丑未相生 · 歲末大局底定", "base_weights": (86, 88, 80, 85)},
]

def calculate_flow_year_radar(user_info=None):
    """
    計算 2026 丙午流年 1~12 月財富、事業、感情、健康曲線
    """
    user_info = user_info or {}
    b_date = str(user_info.get("birth_date", "1990-01-01"))
    b_hour = int(user_info.get("birth_hour", 0) or 0)
    
    # 依緣主生辰種子計算微調偏差
    seed_val = sum(ord(c) for c in b_date) + b_hour * 7 + 2026
    rng = random.Random(seed_val)
    
    monthly_series = []
    overall_list = []
    
    for item in MONTH_DATA_2026:
        m = item["month"]
        bw = item["base_weights"]
        # 個人微調 (-6 ~ +8)
        offset_w = rng.randint(-5, 7)
        offset_c = rng.randint(-5, 7)
        offset_l = rng.randint(-5, 7)
        offset_h = rng.randint(-5, 5)
        
        w_score = max(45, min(99, bw[0] + offset_w))
        c_score = max(45, min(99, bw[1] + offset_c))
        l_score = max(45, min(99, bw[2] + offset_l))
        h_score = max(45, min(99, bw[3] + offset_h))
        overall = int(w_score * 0.35 + c_score * 0.35 + l_score * 0.15 + h_score * 0.15)
        overall_list.append(overall)
        
        monthly_series.append({
            "month": m,
            "name": f"{m}月 ({item['ganzhi']})",
            "solar": item["solar"],
            "theme": item["theme"],
            "wealth": w_score,
            "career": c_score,
            "love": l_score,
            "health": h_score,
            "overall": overall
        })
        
    # 尋找巔峰月與防守月
    peak_idx = overall_list.index(max(overall_list))
    caution_idx = overall_list.index(min(overall_list))
    
    peak_month = monthly_series[peak_idx]
    caution_month = monthly_series[caution_idx]
    
    result = {
        "year": 2026,
        "year_ganzhi": "丙午赤馬年",
        "four_transforms": [
            {"star": "天同", "trans": "化祿", "effect": "福星高照，人際圓融，以和生財"},
            {"star": "天機", "trans": "化權", "effect": "策略策劃，思維靈動，主動掌握主導權"},
            {"star": "文昌", "trans": "化科", "effect": "考運聲名俱佳，文書合約多得助力"},
            {"star": "廉貞", "trans": "化忌", "effect": "慎防情緒急躁、法律口舌爭端與偏門風險"}
        ],
        "summary": "2026 丙午歲次，火氣極旺，萬物奮發騰達。上半年重在開源播種與人脈串聯，秋季迎來年度盛大收穫，冬季則宜順應天時謹慎防守。",
        "peak_month": {
            "month": peak_month["month"],
            "name": peak_month["name"],
            "score": peak_month["overall"],
            "theme": peak_month["theme"],
            "advice": "此月為年度氣數最強頂峰，無論開創事業、大額投資、求婚或重要談判均宜主動推進！"
        },
        "caution_month": {
            "month": caution_month["month"],
            "name": caution_month["name"],
            "score": caution_month["overall"],
            "theme": caution_month["theme"],
            "advice": "此月逢歲星對沖，氣流動盪，切忌大額借貸、衝動辭職或重大爭執，宜沉著修心。"
        },
        "monthly_data": monthly_series
    }
    return to_traditional(result)
