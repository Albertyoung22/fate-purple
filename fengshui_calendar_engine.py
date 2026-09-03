# -*- coding: utf-8 -*-
"""
紫微天機 · 家宅九宮飛星風水與開運日曆核心引擎 (Feng Shui & Destiny Calendar Engine)
支援：
1. 現代家宅九宮飛星方位吉凶判定、化煞招財佈局、東四命/西四命速查。
2. 緣主專屬流日吉凶開運日曆與 iCalendar (.ics) 檔案生成（一鍵匯入 Google / Apple Calendar）。
"""

from datetime import datetime, timedelta
import math

# 2026 丙午年 / 當前流年紫白九宮飛星方位分佈 (中宮與八方)
# 2026 丙午年：一白入中宮
FLYING_STARS_2026 = {
    "center": {"star": "一白貪狼星", "elem": "水", "nature": "吉", "field": "桃花、人緣、名氣", "advice": "中宮水氣靈動，宜保持明亮潔淨，利升職與廣結人脈。"},
    "north": {"star": "七赤破軍星", "elem": "金", "nature": "凶", "field": "破耗、口舌、盜賊", "advice": "正北防金水過旺引起口角破耗，宜置放黑曜石或安忍水化解。"},
    "south": {"star": "六白武曲星", "elem": "金", "nature": "吉", "field": "偏財、權威、貴人", "advice": "正南為偏財與將星位，宜擺放金屬飾品或黃水晶聚寶盆催旺偏財。"},
    "east": {"star": "九紫右弼星", "elem": "火", "nature": "大吉", "field": "喜慶、姻緣、大財", "advice": "正東為九運當旺喜慶星，宜擺放紅色飾物、紫水晶或常青綠植，催旺喜事。"},
    "west": {"star": "五黃廉貞星", "elem": "土", "nature": "大凶", "field": "疾厄、災禍、動盪", "advice": "正西為五黃大煞位，切忌動土修造與紅色亮光，宜掛六帝銅錢或銅葫蘆化煞。"},
    "northeast": {"star": "三碧祿存星", "elem": "木", "nature": "凶", "field": "是非、爭鬥、官非", "advice": "東北防木氣爭競，忌放綠色植物，宜點一盞紅暖燈化解是非口舌。"},
    "northwest": {"star": "二黑巨門星", "elem": "土", "nature": "凶", "field": "病符、健康、憂鬱", "advice": "西北為病符位，忌堆放雜物，宜置放銅葫蘆或化煞銅鈴保全家安康。"},
    "southeast": {"star": "八白左輔星", "elem": "土", "nature": "吉", "field": "正財、田產、置業", "advice": "東南為正財吉位，宜保持通風採光，擺放五穀豐登聚寶盆利正財收入。"},
    "southwest": {"star": "四綠文曲星", "elem": "木", "nature": "吉", "field": "學業、考運、文昌", "advice": "西南為文昌文曲位，利求學升遷，宜擺放四支富貴竹或文昌塔。"}
}

def analyze_fengshui_home(facing_direction="坐北朝南", house_type="住宅公寓"):
    """
    計算現代家宅風水吉凶佈局
    """
    grid = FLYING_STARS_2026
    
    # 根據坐向標註大門吉凶與財位
    direction_map = {
        "坐北朝南": {"door": "south", "wealth": "east", "study": "southwest", "danger": "west"},
        "坐南朝北": {"door": "north", "wealth": "east", "study": "southwest", "danger": "northwest"},
        "坐東朝西": {"door": "west", "wealth": "southeast", "study": "southwest", "danger": "northwest"},
        "坐西朝東": {"door": "east", "wealth": "south", "study": "southwest", "danger": "west"},
        "坐西北朝東南": {"door": "southeast", "wealth": "east", "study": "southwest", "danger": "west"},
        "坐東南朝西北": {"door": "northwest", "wealth": "south", "study": "southwest", "danger": "west"},
        "坐東北朝西南": {"door": "southwest", "wealth": "east", "study": "southwest", "danger": "northwest"},
        "坐西南朝東北": {"door": "northeast", "wealth": "southeast", "study": "southwest", "danger": "west"}
    }
    
    target = direction_map.get(facing_direction, direction_map["坐北朝南"])
    
    return {
        "year": "2026 丙午年",
        "facing": facing_direction,
        "stars_grid": grid,
        "key_spots": {
            "財位推薦": f"正東方（九紫喜慶財星）與東南方（八白正財星）",
            "文昌位推薦": f"西南方（四綠文曲星，宜放文竹或文昌筆）",
            "避忌煞位": f"正西方（五黃煞）與西北方（二黑病符），切忌動土噪音",
            "大門氣場": f"朝向【{facing_direction.split('朝')[-1]}】，逢【{grid[target['door']]['star']}】，{grid[target['door']]['advice']}"
        }
    }

def generate_ics_calendar(user_name="緣主", start_date_str=None, days_count=30):
    """
    生成緣主專屬流日吉凶開運 iCalendar (.ics) 內容
    """
    if not start_date_str:
        now = datetime.now()
    else:
        try:
            now = datetime.strptime(start_date_str, "%Y-%m-%d")
        except:
            now = datetime.now()
            
    events = []
    
    # 週期性吉凶星律
    fortune_cycle = [
        ("🌟 貴人天乙日", "吉星臨門，宜簽約談判、拜訪貴人、求職提報。財神方位：正東。", "HIGHEST"),
        ("💰 正財偏財大旺日", "財帛宮共振，利收帳、理財規劃、促銷進展。開運色：金黃色。", "HIGH"),
        ("💖 桃花紅鸞心動日", "人際魅力四射，宜約會告白、破冰化解誤會、拓展社交。開運物：粉水晶。", "NORMAL"),
        ("⚡ 宜守成平順日", "按部就班，不宜急進，處理文書合約需細心覆核。", "LOW"),
        ("⚠️ 慎防破財口舌日", "擎羊陀羅暗動，切忌借貸、衝動消費、與人爭辯。宜靜坐修心。", "CRITICAL"),
        ("🚀 事業突破躍進日", "官祿文昌護持，宜啟動新專案、展現領導力。利東南方。", "HIGH"),
        ("🧘 休養生息福德日", "放慢腳步，陪伴家人、走入大自然，能大幅蓄積好運能量。", "NORMAL")
    ]
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FatePurple Master//Destiny Calendar V3.0//ZH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:紫微天機 · {user_name}專屬開運日曆",
        "X-WR-TIMEZONE:Asia/Taipei"
    ]
    
    for i in range(days_count):
        cur_day = now + timedelta(days=i)
        day_str = cur_day.strftime("%Y%m%d")
        cycle_idx = (cur_day.toordinal() + hash(user_name)) % len(fortune_cycle)
        title, desc, priority = fortune_cycle[cycle_idx]
        
        event_lines = [
            "BEGIN:VEVENT",
            f"UID:fate-{user_name}-{day_str}@fatepurple.com",
            f"DTSTAMP:{day_str}T000000Z",
            f"DTSTART;VALUE=DATE:{day_str}",
            f"DTEND;VALUE=DATE:{day_str}",
            f"SUMMARY:【紫微天機】{title}",
            f"DESCRIPTION:{desc}",
            "STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT",
            "END:VEVENT"
        ]
        lines.extend(event_lines)
        
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
