"""
====================================================================
Google OR-Tools (CP-SAT Constraint Programming Solver) 命理演算法核心
====================================================================
本模組將紫微斗數與八字命理體系轉化為多維度約束滿足與最優化問題 (CSP / COP)。
採用與頂尖排課系統核心相同的 Google OR-Tools CP-SAT 求解器，
透過整數決策變數 (IntVar)、布林開關變數 (BoolVar)、線性約束 (LinearConstraint)、
互斥約束 (AddAtMostOne / AddExactlyOne) 與目標函數最大化，
對命盤能量、宮位互涉、生年生剋、五行流轉與時空吉凶進行全域最優化求解。
"""

import os
import sys
import time
import math
import collections
try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    cp_model = None
    HAS_ORTOOLS = False

# 12 地支與 10 天干
STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 五行對應
ELEMENT_MAP = {
    "甲": "wood", "乙": "wood", "寅": "wood", "卯": "wood",
    "丙": "fire", "丁": "fire", "巳": "fire", "午": "fire",
    "戊": "earth", "己": "earth", "辰": "earth", "戌": "earth", "丑": "earth", "未": "earth",
    "庚": "metal", "辛": "metal", "申": "metal", "酉": "metal",
    "壬": "water", "癸": "water", "亥": "water", "子": "water"
}

ELEMENT_NAMES = {
    "wood": "木 (仁德·生機·創發)",
    "fire": "火 (光明·熱忱·禮儀)",
    "earth": "土 (穩重·承載·信用)",
    "metal": "金 (果決·義理·規矩)",
    "water": "水 (智識·流動·洞察)"
}

ELEMENT_COLORS = {
    "wood": "蒼青翠綠、草綠色、木質色",
    "fire": "赤紅、絳紫、粉橙、亮珊瑚色",
    "earth": "帝黃、琥珀棕、暖卡其色",
    "metal": "純白、月銀、鉑金、米白色",
    "water": "玄黑、湛藍、藏青、深黛色"
}

PALACE_STANDARD = [
    "命宮", "兄弟宮", "夫妻宮", "子女宮", "財帛宮", "疾厄宮",
    "遷移宮", "奴僕宮", "官祿宮", "田宅宮", "福德宮", "父母宮"
]

MAJOR_STARS = {
    "紫微": {"base": 22, "elem": "earth", "trait": "帝王之尊，統禦全域，具領袖開創格局與自尊風範"},
    "天府": {"base": 20, "elem": "earth", "trait": "南斗令星，庫存充盈，善理財守成、深謀遠慮且處事穩健"},
    "太陽": {"base": 18, "elem": "fire", "trait": "光芒普照，博愛仗義，熱忱好施，利名聲與公眾拓展"},
    "太陰": {"base": 18, "elem": "water", "trait": "月曜清澄，心思縝密，主富厚置產與細膩策劃深謀"},
    "武曲": {"base": 20, "elem": "metal", "trait": "正財星宿，剛毅果決，重實踐不尚空談，善執行致富"},
    "天同": {"base": 15, "elem": "water", "trait": "福德之星，溫柔敦厚，貴人運隆，重生活情調與人和"},
    "廉貞": {"base": 17, "elem": "fire", "trait": "次桃花與事業雄心，公關交際強，具政治直覺與獨特審美"},
    "天機": {"base": 17, "elem": "wood", "trait": "智慧謀略，應變神速，擅策略分析、數理推演與專業技藝"},
    "貪狼": {"base": 16, "elem": "wood", "trait": "第一桃花與才藝之曜，靈活多變，喜創投突破與跨界探索"},
    "巨門": {"base": 14, "elem": "water", "trait": "暗曜是非與辯才之星，洞察深邃，善口才演說、分析諮詢"},
    "天相": {"base": 16, "elem": "water", "trait": "宰相印璽，輔佐周全，重誠信契約、協調協同與形象名譽"},
    "天梁": {"base": 17, "elem": "earth", "trait": "蔭星壽相，老成持重，逢凶化吉，具長者風範與監察正氣"},
    "七殺": {"base": 16, "elem": "metal", "trait": "將星威權，獨當一面，敢闖敢拼，利開拓先鋒與破浪斬棘"},
    "破軍": {"base": 15, "elem": "water", "trait": "破耗先驅，破舊立新，勇於革新變革，不畏艱難冒險"}
}

AUX_STARS = {
    "左輔": 10, "右弼": 10, "天魁": 12, "天鉞": 12, "文昌": 10, "文曲": 10,
    "祿存": 15, "天馬": 10, "天喜": 8, "紅鸞": 8, "三台": 5, "八座": 5
}

SHA_STARS = {
    "擎羊": 14, "陀羅": 14, "火星": 12, "鈴星": 12, "地空": 15, "地劫": 15,
    "化忌": 25, "天刑": 10, "陰煞": 8
}

DIRECTIONS = [
    ("坎北 (水)", "water", 0),
    ("艮東北 (土)", "earth", 1),
    ("震東 (木)", "wood", 2),
    ("巽東南 (木)", "wood", 3),
    ("離南 (火)", "fire", 4),
    ("坤西南 (土)", "earth", 5),
    ("兌西 (金)", "metal", 6),
    ("乾西北 (金)", "metal", 7)
]


class FateCPSATSolver:
    """
    Google OR-Tools CP-SAT 命理約束規劃求解器
    """
    def __init__(self, chart_data=None, user_info=None, prompt="", matched_rules=None):
        self.chart_data = chart_data or []
        self.user_info = user_info or {}
        self.prompt = prompt or ""
        self.matched_rules = matched_rules or []
        
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solved = False
        self.solve_status = None
        self.solve_stats = {}
        
        # 決策變數
        self.palace_vars = {}        # 12宮位能量: 0 ~ 100
        self.element_vars = {}       # 五行能量: 0 ~ 100
        self.direction_vars = {}     # 8方位布林開關
        self.timing_vars = {}        # 12時辰布林開關
        
        # 求解結果
        self.palace_scores = {}
        self.element_scores = {}
        self.best_direction = None
        self.best_timing = None
        self.objective_val = 0
        self.wall_time = 0.0

    def build_model(self):
        """構建 CP-SAT 數學模型與約束條件"""
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.palace_vars = {}
        self.element_vars = {}
        self.direction_vars = {}
        self.timing_vars = {}
        
        # 1. 宮位能量整數變數 (Palace Energy: 0~100)
        for i in range(12):
            self.palace_vars[i] = self.model.NewIntVar(0, 100, f'palace_{i}_energy')

        # 2. 五行平衡整數變數 (Five Elements: 0~100)
        elements = ["wood", "fire", "earth", "metal", "water"]
        for e in elements:
            self.element_vars[e] = self.model.NewIntVar(0, 100, f'element_{e}')

        # 3. 空間方位決策 (Exact 1 Direction)
        for d_idx, (d_name, _, _) in enumerate(DIRECTIONS):
            self.direction_vars[d_idx] = self.model.NewBoolVar(f'dir_{d_idx}')
        self.model.AddExactlyOne(self.direction_vars.values())

        # 4. 天時時辰決策 (Exact 1 Timing)
        for b_idx, b_name in enumerate(BRANCHES):
            self.timing_vars[b_idx] = self.model.NewBoolVar(f'timing_{b_idx}')
        self.model.AddExactlyOne(self.timing_vars.values())

        # -------------------------------------------------------------
        # 計算命盤原始基底權重 (Domain Knowledge Encoding)
        # -------------------------------------------------------------
        palace_raw_bases = {}
        sihua_bonus = collections.defaultdict(int)
        sha_penalties = collections.defaultdict(int)

        for item in self.chart_data:
            idx = item.get("id")
            if idx is None or idx < 0 or idx >= 12:
                continue
            
            stars = item.get("stars", [])
            base_score = 48
            
            for s in stars:
                s_name = s.get("name", "") if isinstance(s, dict) else str(s)
                clean_name = s_name.split(' ')[0].split('(')[0]
                s_trans = s.get("transformation") or s.get("trans", "") if isinstance(s, dict) else ""
                
                # 主星賦權
                if clean_name in MAJOR_STARS:
                    base_score += MAJOR_STARS[clean_name]["base"]
                # 吉星賦權
                if clean_name in AUX_STARS:
                    base_score += AUX_STARS[clean_name]
                # 煞星扣分
                if clean_name in SHA_STARS:
                    sha_penalties[idx] += SHA_STARS[clean_name]
                
                # 四化注入
                if s_trans in ["化祿", "hua_lu"] or clean_name == "化祿":
                    sihua_bonus[idx] += 24
                elif s_trans in ["化權", "hua_quan"] or clean_name == "化權":
                    sihua_bonus[idx] += 18
                elif s_trans in ["化科", "hua_ke"] or clean_name == "化科":
                    sihua_bonus[idx] += 15
                elif s_trans in ["化忌", "hua_ji"] or clean_name == "化忌":
                    sha_penalties[idx] += 26
                    opp_idx = (idx + 6) % 12
                    sha_penalties[opp_idx] += 14

            palace_raw_bases[idx] = min(96, max(12, base_score))

        for i in range(12):
            if i not in palace_raw_bases:
                palace_raw_bases[i] = 48

        # 約束條件 1: 宮位能量上下界約束 (Bound Constraints)
        for i in range(12):
            net_base = palace_raw_bases[i] + sihua_bonus[i] - sha_penalties[i]
            lb = max(10, min(88, net_base - 14))
            ub = max(25, min(100, net_base + 14))
            self.model.Add(self.palace_vars[i] >= lb)
            self.model.Add(self.palace_vars[i] <= ub)

        # 約束條件 2: 三方四正連鎖互涉約束 (Triangular Coupling Constraints)
        # 命宮 (0)、財帛 (4)、官祿 (8)、遷移 (6)
        life_idx, wealth_idx, travel_idx, career_idx = 0, 4, 6, 8
        self.model.Add(self.palace_vars[life_idx] * 2 >= self.palace_vars[career_idx] + self.palace_vars[wealth_idx] - 28)
        self.model.Add(self.palace_vars[life_idx] * 2 <= self.palace_vars[career_idx] + self.palace_vars[wealth_idx] + 28)
        self.model.Add(self.palace_vars[travel_idx] + self.palace_vars[life_idx] >= 55)

        # 約束條件 3: 五行能量總合守恆與平順約束 (Element Conservation)
        self.model.Add(sum(self.element_vars.values()) == 250)
        for e in elements:
            self.model.Add(self.element_vars[e] >= 18)
            self.model.Add(self.element_vars[e] <= 82)
            
        # 相生鏈條約束
        self.model.Add(self.element_vars["fire"] >= self.element_vars["wood"] - 26)
        self.model.Add(self.element_vars["earth"] >= self.element_vars["fire"] - 26)
        self.model.Add(self.element_vars["metal"] >= self.element_vars["earth"] - 26)
        self.model.Add(self.element_vars["water"] >= self.element_vars["metal"] - 26)
        self.model.Add(self.element_vars["wood"] >= self.element_vars["water"] - 26)

        # 約束條件 4: 六沖地支避險約束 (Hard Clash Avoidance)
        zodiac_clash_map = {
            "鼠": 6, "牛": 7, "虎": 8, "兔": 9, "龍": 10, "蛇": 11,
            "馬": 0, "羊": 1, "猴": 2, "雞": 3, "狗": 4, "豬": 5
        }
        user_zodiac = self.user_info.get("zodiac", "")
        if user_zodiac in zodiac_clash_map:
            clash_b = zodiac_clash_map[user_zodiac]
            self.model.Add(self.timing_vars[clash_b] == 0)

        # -------------------------------------------------------------
        # 目標函數 (Objective: Maximize Harmony & Lucky Energy)
        # -------------------------------------------------------------
        weighted_palaces = (
            self.palace_vars[life_idx] * 3 +
            self.palace_vars[wealth_idx] * 2 +
            self.palace_vars[career_idx] * 2 +
            self.palace_vars[travel_idx] * 1 +
            self.palace_vars[10] * 1 # 福德宮
        )
        total_penalties = sum(sha_penalties.values())
        harmony_term = sum(self.element_vars[e] for e in elements)
        
        self.model.Maximize(weighted_palaces + harmony_term - total_penalties)

    def solve(self, time_limit_seconds=3.0):
        """執行 Google OR-Tools CP-SAT 求解器"""
        start_time = time.time()
        self.build_model()
        
        self.solver.parameters.max_time_in_seconds = time_limit_seconds
        self.solver.parameters.num_search_workers = 4
        
        self.solve_status = self.solver.Solve(self.model)
        self.wall_time = round(time.time() - start_time, 4)
        
        if self.solve_status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            self.solved = True
            self.objective_val = int(self.solver.ObjectiveValue())
            
            for i in range(12):
                p_name = PALACE_STANDARD[i]
                self.palace_scores[p_name] = int(self.solver.Value(self.palace_vars[i]))
            
            for e in ["wood", "fire", "earth", "metal", "water"]:
                self.element_scores[e] = int(self.solver.Value(self.element_vars[e]))
            
            for d_idx, (d_name, _, _) in enumerate(DIRECTIONS):
                if self.solver.Value(self.direction_vars[d_idx]):
                    self.best_direction = d_name
                    break
            
            for b_idx, b_name in enumerate(BRANCHES):
                if self.solver.Value(self.timing_vars[b_idx]):
                    self.best_timing = f"{b_name}時 ({b_idx*2:02d}:00 - {(b_idx*2+2)%24:02d}:00)"
                    break

            self.solve_stats = {
                "status": "OPTIMAL (全局最優解)" if self.solve_status == cp_model.OPTIMAL else "FEASIBLE (可行解)",
                "wall_time": self.wall_time,
                "branches": self.solver.NumBranches(),
                "conflicts": self.solver.NumConflicts(),
                "objective": self.objective_val
            }
            return True
        else:
            self.solved = False
            self.solve_stats = {
                "status": "INFEASIBLE (約束衝突，無可行解)",
                "wall_time": self.wall_time
            }
            return False

    # =========================================================================
    # 命盤結構與星曜解析器 (Chart Details Extractor)
    # =========================================================================
    def _extract_palace(self, palace_name):
        """從 chart_data 中提取指定宮位之詳細數據 (地支、天干、主星、吉星、煞星、是否為身宮)"""
        for p in self.chart_data:
            p_name = p.get("palaceName", "")
            if palace_name in p_name:
                zhi = p.get("zhi", "")
                gan = p.get("gan", "")
                is_body = p.get("isBody", False)
                is_life = p.get("isLife", False)
                stars = p.get("stars", [])
                
                main_stars = []
                aux_stars = []
                sha_stars = []
                all_star_names = []
                
                for s in stars:
                    s_name = s.get("name", "") if isinstance(s, dict) else str(s)
                    clean_name = s_name.split(' ')[0].split('(')[0]
                    brightness = s.get("brightness", "") if isinstance(s, dict) else ""
                    if brightness and brightness in ["廟", "旺", "利", "得", "平", "不", "陷"]:
                        full_name = f"{clean_name}({brightness})"
                    else:
                        full_name = clean_name
                        
                    all_star_names.append(clean_name)
                    if clean_name in MAJOR_STARS:
                        main_stars.append(full_name)
                    elif clean_name in AUX_STARS:
                        aux_stars.append(full_name)
                    elif clean_name in SHA_STARS or "化忌" in clean_name:
                        sha_stars.append(full_name)
                        
                return {
                    "palace_name": p_name,
                    "zhi": zhi,
                    "gan": gan,
                    "is_body": is_body,
                    "is_life": is_life,
                    "main_stars": main_stars,
                    "aux_stars": aux_stars,
                    "sha_stars": sha_stars,
                    "all_stars": all_star_names,
                    "score": self.palace_scores.get(palace_name, 70)
                }
        return {
            "palace_name": palace_name,
            "zhi": "卯",
            "gan": "甲",
            "is_body": False,
            "is_life": False,
            "main_stars": [],
            "aux_stars": [],
            "sha_stars": [],
            "all_stars": [],
            "score": self.palace_scores.get(palace_name, 70)
        }

    def _get_body_palace(self):
        """尋找命盤中身宮寄託之宮位"""
        for p in self.chart_data:
            if p.get("isBody", False):
                return p.get("palaceName", "命宮")
        return "命宮"

    def _detect_star_patterns(self, sanfang_stars):
        """偵測三方四正大格局"""
        all_s = set(sanfang_stars)
        patterns = []
        if {"七殺", "破軍", "貪狼"}.intersection(all_s):
            if all(k in all_s for k in ["七殺", "破軍", "貪狼"]):
                patterns.append("【殺破狼開創格】（人生開拓動能充沛，勇於打破常規、敢為天下先）")
            elif "七殺" in all_s or "破軍" in all_s:
                patterns.append("【大將拓荒格】（具備極強的執行魄力與拓荒意志）")
                
        if all(k in all_s for k in ["天機", "太陰", "天同", "天梁"]) or len({"天機", "太陰", "天同", "天梁"}.intersection(all_s)) >= 3:
            patterns.append("【機月同梁格】（擅長深謀遠慮、企劃謀略、公教行政與專業幕僚，平穩中出非凡）")
            
        if "紫微" in all_s and "天府" in all_s:
            patterns.append("【紫府同宮/朝垣格】（帝相得位，包容厚重，具領袖風範與福庫底氣）")
        elif "紫微" in all_s:
            patterns.append("【紫微坐照格】（自尊心強，有主見與宏觀視野）")
            
        if "天府" in all_s and "天相" in all_s:
            patterns.append("【府相朝垣格】（衣食豐足，人際協同力佳，深得長輩與夥伴信賴）")
            
        if "太陽" in all_s and "巨門" in all_s:
            patterns.append("【巨日同宮格】（光明化暗，善以口才專業照耀四方，利跨界與公眾事務）")
            
        if "武曲" in all_s and "貪狼" in all_s:
            patterns.append("【武貪格】（少年辛勤磨礪，中年厚積薄發，財藝雙美之象）")
            
        if "祿存" in all_s and "天馬" in all_s:
            patterns.append("【祿馬交馳格】（動中生財，越走動越有發達之機）")
            
        if not patterns:
            patterns.append("【吉星拱照 · 五行和合局】（氣脈平順，厚積薄發）")
            
        return "、".join(patterns)

    def _get_age_and_zodiac(self):
        """安全取得緣主之年齡與生肖"""
        age = self.user_info.get("age", 30)
        birth_str = self.user_info.get("birth_date", "")
        if not age or age == 30:
            try:
                if birth_str and "-" in birth_str:
                    byear = int(birth_str.split("-")[0])
                    import datetime
                    age = datetime.datetime.now().year - byear
            except:
                age = 30
                
        zodiacs = ["猴", "雞", "狗", "豬", "鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊"]
        zodiac_str = self.user_info.get("zodiac", "")
        if not zodiac_str or zodiac_str == "吉瑞":
            try:
                if birth_str and "-" in birth_str:
                    byear = int(birth_str.split("-")[0])
                    zodiac_str = zodiacs[byear % 12]
                else:
                    zodiac_str = "吉瑞"
            except:
                zodiac_str = "吉瑞"
        return age, zodiac_str, birth_str

    def generate_report(self):
        """完整命譜最優化推演解析報告（大師開示）"""
        if not self.solved:
            return "【大師感應】：天機玄妙，星曜交錯產生相斥之氣，請重新校驗生辰與命盤配置。"

        age, zodiac, birth_str = self._get_age_and_zodiac()
        name = self.user_info.get("user_name", "緣主")
        
        sorted_palaces = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)
        top_palaces = sorted_palaces[:3]
        weak_palace = sorted_palaces[-1]
        
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest_element = sorted_elements[0][0]
        strongest_element = sorted_elements[-1][0]
        
        lucky_color = ELEMENT_COLORS.get(weakest_element, "白銀、純金")
        element_desc = ELEMENT_NAMES.get(weakest_element, "生機")
        
        report = []
        report.append("【紫微天機道長 · 命譜乾坤精批】")
        report.append("============================================================")
        report.append("● 命盤定格：紫微拱照 · 神煞得位")
        report.append("● 氣數周天：十二宮度氣脈貫通，五行生剋有情，乾坤定局！")
        report.append("● 天機評斷：氣候周全，順應天時地利必能開花結果。\n")

        report.append(f"緣主 {name}（現年 {age} 歲，生肖屬{zodiac}）：")
        report.append(f"老道凝神為你詳觀命譜，推演十二宮度星曜賦性、三方四正牽連呼應，以及子平八字五行生剋守恆。你這張盤氣象端正，吉曜互為奧援，且聽老道為你層層撥開雲霧：\n")

        report.append("### 📊 一、十二宮位先天能量氣數")
        for p_name, score in self.palace_scores.items():
            bar_len = int(score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            report.append(f"- **{p_name}**: 【{bar}】 {score} 分")
        report.append("")

        report.append("### 🏆 二、大師格局定盤批註")
        report.append(f"1. **命盤最強樞紐位**：【{top_palaces[0][0]}】({top_palaces[0][1]}分)、【{top_palaces[1][0]}】({top_palaces[1][1]}分)、【{top_palaces[2][0]}】({top_palaces[2][1]}分)。")
        report.append(f"   - 此為你命盤中最強盛之「福澤樞紐」，氣場最旺。此生若能依託這三大宮位的優勢領域發展，定能事半功倍、得道多助！")
        report.append(f"2. **需修心安神之位**：【{weak_palace[0]}】({weak_palace[1]}分)。")
        report.append(f"   - 此宮位承受較多星曜磨礪或張力，考驗較多，宜以「靜水流深、以柔克剛」為原則，莫鑽牛角尖。\n")

        report.append("### ☯️ 三、五行中庸平衡與喜用神開示")
        for e_key, e_val in self.element_scores.items():
            report.append(f"- **{ELEMENT_NAMES[e_key]}**: 能量指數 {e_val} / 100")
        report.append(f"\n💡 **大師開運裁定**：緣主命盤最喜【{element_desc}】，宜借天地相生之氣滋養命盤。")
        report.append(f"- **開運吉祥色**：{lucky_color}")
        report.append(f"- **生旺得利吉時**：每日 {self.best_timing}")
        report.append(f"- **開運迎祥方位**：{self.best_direction}\n")

        report.append("### 💡 四、大師點撥：趨吉避凶精準心法")
        report.append(f"1. **現代職場與求財指南**：")
        report.append(f"   - 依據【{top_palaces[0][0]}】的優勢導向，建議深耕具備自主決策權或專業門檻之賽道，切勿陷入人浮於事的繁瑣內耗。")
        report.append(f"   - 求財宜注重週期節奏，借助五行生旺之氣平穩積蓄，不為一時浮躁所動。")
        report.append(f"2. **心態修為與時空借力**：")
        report.append(f"   - 每日可於 {self.best_timing} 處理重要謀劃或簽署要務，多得清明智慧。")
        report.append(f"   - 辦公座椅或臥室床頭可適度面朝【{self.best_direction}】，引動和順磁場，消弭負面干擾。")

        return "\n".join(report)

    # =========================================================================
    # 【核心大師即時諮詢】：命宮、身宮與三方四正深度合參
    # =========================================================================
    def _handle_instant_master_consultation(self, name, clean_q="", prompt=""):
        """大師即時諮詢：深層解析命宮、身宮、三方四正與吉煞格局"""
        age, zodiac_str, birth_str = self._get_age_and_zodiac()
        
        # 提取命盤核心宮位
        ming = self._extract_palace("命宮")
        body_palace_name = self._get_body_palace()
        body = self._extract_palace(body_palace_name)
        cai = self._extract_palace("財帛宮")
        guan = self._extract_palace("官祿宮")
        qian = self._extract_palace("遷移宮")
        fu = self._extract_palace("福德宮")
        
        # 三方四正所有星曜與大格局
        sanfang_stars = ming["all_stars"] + cai["all_stars"] + guan["all_stars"] + qian["all_stars"]
        pattern_desc = self._detect_star_patterns(sanfang_stars)
        
        # 命宮主星字串與性格剖析
        ming_main_str = "、".join(ming["main_stars"]) if ming["main_stars"] else "無主星 (借對宮遷移星曜坐照)"
        ming_aux_str = "、".join(ming["aux_stars"]) if ming["aux_stars"] else "諸吉拱照"
        ming_sha_str = "、".join(ming["sha_stars"]) if ming["sha_stars"] else "煞星未現，氣脈純和"
        
        # 身宮主星字串
        body_main_str = "、".join(body["main_stars"]) if body["main_stars"] else "和潤正曜"
        
        # 財帛、官祿、遷移主星字串
        cai_main_str = "、".join(cai["main_stars"]) if cai["main_stars"] else "得天時生財吉曜"
        guan_main_str = "、".join(guan["main_stars"]) if guan["main_stars"] else "清正事功星宿"
        qian_main_str = "、".join(qian["main_stars"]) if qian["main_stars"] else "四方迎納吉星"
        
        # 五行喜用與開運
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")
        
        # 人生階段定義
        if age <= 25:
            stage_desc = "初涉江湖之潛龍蓄勢期。滿懷熱忱，思維靈活，正是博覽廣涉、扎穩專業功底的黃金年華。"
        elif age <= 35:
            stage_desc = "成家立業與事業衝刺之關鍵攀升期。既承載各方期待與職場重任，又面臨生活開銷與賽道定型之抉擇考驗。"
        elif age <= 50:
            stage_desc = "人生事功之頂峰掌舵與厚積薄發期。見慣風浪，深諳世道，重在資源整合、團隊定海與家庭長遠傳承。"
        else:
            stage_desc = "心性通透之甲子圓融期。閱歷深厚，知進退明得失，重在福慧雙修、傳承晚輩與從容頤養。"

        # 身宮寄託深度剖析
        if body_palace_name == "命宮":
            body_meaning = "【命身同宮】：先天本性與後天言行高度統一。自立自強、有強烈主見與定力，不輕易隨波逐流，凡事以自我實力為立足之本。"
        elif body_palace_name == "官祿宮" or body_palace_name == "事業宮":
            body_meaning = "【身宮寄官祿】：後天事業心極重，極度渴望在職場或專業領域取得實質成就與社會認同，工作成就直接決定內心幸福感。"
        elif body_palace_name == "財帛宮":
            body_meaning = "【身宮寄財帛】：後天極重財務安全感與經濟回報。行事注重成本效益與長遠保障，善於將各項資源轉化為實質資產。"
        elif body_palace_name == "夫妻宮":
            body_meaning = "【身宮寄夫妻】：後天極重感情寄託、伴侶互動與家庭溫暖。婚姻與感情狀態對整個人生心境與事業成敗有深遠牽引作用。"
        elif body_palace_name == "遷移宮":
            body_meaning = "【身宮寄遷移】：後天喜動不喜靜，熱衷外出歷練、廣結人脈。在異鄉、跨界或出外奔波中往往能收穫遠大於原地的機緣。"
        elif body_palace_name == "福德宮":
            body_meaning = "【身宮寄福德】：後天重視精神世界的富足、生活情調與內心安寧。善於調養心境，不願為名利過度犧牲自我自由。"
        else:
            body_meaning = f"【身宮寄於{body_palace_name}】：後天言行與人生重心深受此宮位牽引，注重該領域之和諧圓滿。"

        return (
            f"【紫微天機 · 宗師即時深度諮詢開示】：\n\n"
            f"緣主 {name}（現年 **{age} 歲**，生肖屬**{zodiac_str}**）：\n"
            f"老道凝神為你詳觀紫微命譜十二宮度氣脈，推演星曜坐守、三方四正交馳與五行生剋守恆。\n\n"
            f"當前緣主歲數正行至：★ **{stage_desc}** ★\n"
            f"整張命盤氣象端嚴，三方四正交會格局定為：★ **{pattern_desc}** ★。\n"
            f"且聽老道為你依「命宮、身宮、三方四正與吉煞四化」逐層剖析吉凶機關：\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【一、命宮坐守 · 先天心性與格局底色】\n"
            f"● **命宮方位**：位於地支【**{ming['zhi']}宮**】（氣數底氣 **{ming['score']} 分**）\n"
            f"● **坐守主星**：【**{ming_main_str}**】\n"
            f"● **輔照星曜**：吉曜【{ming_aux_str}】｜ 煞曜【{ming_sha_str}】\n\n"
            f"💡 **宗師定盤**：\n"
            f"命宮坐守【{ming_main_str}】，奠定了你此生外圓內方、有骨氣、重承諾之先天底色。你為人思維縝密，不喜浮誇虛名，做事實事求是。\n"
            f"遇逆境時自有一股倔強與韌勁，絕非輕易言敗之人。唯獨有時要求完美、思慮過重，容易讓自己精神緊繃。\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【二、身宮寄託 · 後天追求與精神風骨】\n"
            f"● **身宮落位**：寄於【**{body_palace_name}**】（地支【{body['zhi']}宮】）\n"
            f"● **坐守星曜**：【**{body_main_str}**】\n\n"
            f"💡 **宗師解碼**：\n"
            f"身宮乃三十歲後人生行事風骨與後天執念之所在。盤中顯示：{body_meaning}\n"
            f"先天之命宮賦予你天賦才智，而後天身宮則是你全力奮鬥之舞台，兩者相輔相成，定能開創非凡基業！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【三、三方四正 · 氣數周天與功名財氣合參】\n"
            f"● **【財帛宮】（位於{cai['zhi']}宮 · {cai['score']}分）**：坐守【**{cai_main_str}**】。\n"
            f"  - **求財指引**：正財根基雄厚，利於憑藉專業技術、管理謀略或長線佈局生財。切忌高槓桿投機盲賭，穩紮穩打自能聚沙成塔。\n\n"
            f"● **【官祿宮】（位於{guan['zhi']}宮 · {guan['score']}分）**：坐守【**{guan_main_str}**】。\n"
            f"  - **事業前程**：適合在具備決策權、技術主導性或專業門檻的賽道深耕，不宜在平庸內耗的環境中虛擲光陰。\n\n"
            f"● **【遷移宮】（位於{qian['zhi']}宮 · {qian['score']}分）**：坐守【**{qian_main_str}**】。\n"
            f"  - **出外際遇**：出外有貴人相助，多向外走動、拓展人脈或跨界學習，格局必能越走越寬。\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【四、吉星煞曜與四化引動之玄機】\n"
            f"● **吉曜庇蔭**：盤中得吉星會照，代表你在關鍵時刻總有貴人暗中相挺，常能逢凶化吉。\n"
            f"● **化煞為用**：盤中縱有煞星磨礪，亦是玉不琢不成器之過程。煞星之剛烈正可轉化為你專注破局之強大執行力，無須懼怕！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【五、宗師點撥 · 人生當前關竅與修心錦囊】\n"
            f"1. **【心態安神】**：世事如棋局局新，切莫為眼前一時得失擾亂心神。「急則生亂，緩則圓通」，遇重大決策先沉靜三日。\n"
            f"2. **【行事準則】**：深耕核心長板，多與正向貴人結緣，遠離是非口舌。\n"
            f"3. **【生旺天時吉方】**：\n"
            f"   - 每日最利決策吉時為：★ **{self.best_timing}** ★\n"
            f"   - 第一生旺大吉方位為：★ **{self.best_direction}** ★\n"
            f"   - 開運調和色系：日常宜多搭配 **{lucky_color}** 系衣飾調和磁場。\n\n"
            f"✦ 【老道定心真言】\n"
            f"『順天應人，厚德載物。』只要心持正念、順應時節，前路必定天寬地闊、福祿相隨！"
        )

    def answer_query(self, prompt, target_type="chat"):
        """根據緣主提問，由大師口吻給予精準具體指引"""
        if not self.solved:
            self.solve()
            
        p_lower = prompt.lower()
        age, zodiac_str, _ = self._get_age_and_zodiac()
        name = self.user_info.get("user_name", "緣主")
        
        # 精準提取用戶真實提問，徹底隔離背景命盤資訊與系統指令
        clean_q = prompt
        
        # 先以常見的分隔標記與系統指令標籤截斷尾部
        for tail_marker in ["\n\n【大師指令】", "\n\n【特別要求】", "\n\n(請強制使用", "\n【最高優先權指令】"]:
            if tail_marker in clean_q:
                clean_q = clean_q.split(tail_marker)[0]

        # 再提取提問標籤後方的真正提問內容
        for head_marker in ["--------------------------------------------------", "【緣主提問】：", "【緣主提問】", "【緣主祈求】：", "【緣主祈求】", "【提問】：", "【提問】", "用戶提問：「", "用戶提問：", "用戶測字：「", "用戶測字："]:
            if head_marker in clean_q:
                clean_q = clean_q.split(head_marker)[-1]
                break
        
        # 若仍有多段，剔除背景段落並取得用戶提問段落
        raw_paras = [p.strip() for p in clean_q.split("\n\n") if p.strip()]
        valid_paras = [
            p for p in raw_paras
            if not any(p.startswith(prefix) for prefix in ["【重要：緣主", "【當下天時", "【時空宮位", "【特別要求】", "(請強制", "請務必結合"])
        ]
        if valid_paras:
            clean_q = valid_paras[-1]
        
        # 計算純粹淨化的提問 (剔除標點符號與前後引號)
        actual_q = clean_q.strip("」」：「」 \t\r\n。！,!?！？")

        # =========================================================================
        # 第一優先級：明確要求「大師即時諮詢」或「命宮身宮三方四正」
        # =========================================================================
        if (any(kw in clean_q for kw in ["大師即時諮詢", "即時諮詢", "命宮、身宮", "身宮與三方四正", "三方四正", "綜合命盤解析", "大師諮詢", "命宮主星與格局"]) or
            any(kw in prompt for kw in ["【大師即時諮詢】", "《紫微綜合命盤解析》"])):
            return self._handle_instant_master_consultation(name, clean_q, prompt=prompt)

        # =========================================================================
        # 第二優先級：前端明確指定之 target_type 專案分流
        # =========================================================================
        if target_type == "love":
            return self._handle_love(name)
        elif target_type == "pastLife":
            return self._handle_past_life(name)
        elif target_type == "glyph":
            return self._handle_glyph(name, clean_q, prompt=prompt)
        elif target_type == "dream":
            return self._handle_dream(name)
        elif target_type == "stock":
            return self._handle_stock(name, clean_q)
        elif target_type == "bazi":
            return self._handle_bazi(name)
        elif target_type == "simple":
            return self._handle_simple(name)
        elif target_type == "report":
            return self.generate_report()
        elif target_type == "daily":
            if any(kw in clean_q for kw in ["出門吉位", "吉位", "避諱", "歲時禁忌", "歲時避諱", "歲時", "出行", "出門"]):
                return self._handle_omens(name)
            else:
                return self._handle_daily(name)
        elif target_type == "finance":
            if any(kw in clean_q for kw in ["號碼", "樂透", "威力彩", "539", "幸運號", "彩券", "偏財"]):
                return self._handle_lucky_numbers(name)
            else:
                return self._handle_finance(name)

        # =========================================================================
        # 第三優先級：緣主自訂提問 (Chat) 依語義精準匹配專題
        # =========================================================================
        # 1. 測字占卜
        if (target_type == "glyph" or 
            any(kw in clean_q for kw in ["測字", "漢字", "文字占卜", "卜字", "拆字", "解字", "字相", "觀字", "測一字", "幫我測", "請問這個字", "測字：", "測字:"]) or 
            any(kw in prompt for kw in ["用戶測字", "測字占卜"]) or 
            (len(actual_q) <= 2 and any('\u4e00' <= c <= '\u9fff' for c in actual_q) and not any(kw in actual_q for kw in ["運勢", "健康", "工作", "財運", "婚姻", "十年", "八字", "事業", "股市", "股票", "官祿", "疾厄", "田宅", "父母", "兄弟", "奴僕"]))):
            return self._handle_glyph(name, clean_q, prompt=prompt)

        # 2. 幸運號碼與偏財
        elif any(kw in clean_q for kw in ["號碼", "樂透", "威力彩", "539", "幸運號", "彩券", "偏財", "明牌", "靈動數"]):
            return self._handle_lucky_numbers(name)

        # 3. 出門吉位與避諱
        elif any(kw in clean_q for kw in ["出門吉位", "吉位", "避諱", "歲時禁忌", "歲時避諱", "歲時", "出行", "出門", "禁忌"]):
            return self._handle_omens(name)

        # 4. 防小人與化解是非口舌
        elif any(kw in clean_q for kw in ["小人", "防小人", "避小人", "犯小人", "招小人", "是非", "口舌", "背刺", "陷害", "交友", "奴僕宮"]):
            return self._handle_villain(name)

        # 5. 招貴人與人脈通達
        elif any(kw in clean_q for kw in ["貴人", "招貴人", "貴人運", "提攜", "賞識", "相助", "人脈", "伯樂", "結緣"]):
            return self._handle_benefactor(name)

        # 6. 田宅置產與房產風水
        elif any(kw in clean_q for kw in ["買房", "買屋", "置產", "田宅", "房產", "不動產", "賣房", "搬家", "入厝", "裝潢", "宅基"]):
            return self._handle_property(name)

        # 7. 考運功名與學業升遷
        elif any(kw in clean_q for kw in ["考試", "考運", "學業", "讀書", "升學", "國考", "公職", "證照", "文昌", "考績"]):
            return self._handle_exam(name)

        # 8. 出國遠行與異鄉發展
        elif any(kw in clean_q for kw in ["出國", "遠行", "留學", "移民", "出差", "赴外", "離鄉", "外派", "遷移宮"]):
            return self._handle_travel(name)

        # 9. 子女緣分與求子育嗣
        elif any(kw in clean_q for kw in ["求子", "生子", "懷孕", "備孕", "子女", "孩子", "小孩", "生男生女", "子息", "育兒", "子女宮"]):
            return self._handle_children(name)

        # 10. 婚姻和諧與白頭偕老
        elif any(kw in clean_q for kw in ["婚姻", "結婚", "成家", "配偶", "老婆", "老公", "外遇", "出軌", "第三者", "婆媳", "離婚"]):
            return self._handle_marriage(name)

        # 11. 桃花感情與戀愛正緣
        elif any(kw in clean_q for kw in ["桃花", "感情", "戀愛", "另一半", "對象", "姻緣", "脫單", "復合", "伴侶", "情緣", "正緣"]):
            return self._handle_love(name)

        # 12. 財運與求財投資
        elif any(kw in clean_q for kw in ["財", "錢", "投資", "理財", "發財", "財帛", "求財", "賺錢", "資產", "漏財", "破財", "財庫"]):
            return self._handle_finance(name)

        # 13. 開運轉運與化解厄運
        elif any(kw in clean_q for kw in ["改運", "轉運", "化太歲", "犯太歲", "安太歲", "祈福", "消災", "消業", "厄運", "開運"]):
            return self._handle_luck_transformation(name)

        # 14. 父母長輩與孝親福報
        elif any(kw in clean_q for kw in ["父母", "長輩", "父親", "母親", "爸爸", "媽媽", "孝親", "祖蔭", "父母宮"]):
            return self._handle_parents(name)

        # 15. 事業與工作
        elif any(kw in clean_q for kw in ["工作", "事業", "職業", "升遷", "跳槽", "創業", "官祿", "求職", "職場", "合夥"]):
            return self._handle_career(name)

        # 16. 健康與疾厄
        elif any(kw in clean_q for kw in ["健康", "疾厄", "身體", "作息", "疾病", "調養", "睡眠", "體魄", "養生"]):
            return self._handle_health(name)

        # 17. 十年大限
        elif any(kw in clean_q for kw in ["十年大限", "大限運勢", "十年大運", "十年運程", "大限", "十年"]):
            return self._handle_decade(name, age)

        # 18. 流年運勢
        elif any(kw in clean_q for kw in ["流年運勢", "今年運勢", "流年", "今年", "歲運", "年運"]):
            return self._handle_yearly(name)

        # 19. 流月運勢
        elif any(kw in clean_q for kw in ["流月運勢", "本月運勢", "流月", "本月", "月令", "月運"]):
            return self._handle_monthly(name)

        # 20. 股市股票
        elif any(kw in clean_q for kw in ["股票", "股價", "股市", "大盤", "個股", "代號"]):
            return self._handle_stock(name, clean_q)

        # 21. 八字命書
        elif any(kw in clean_q for kw in ["八字詳批", "子平八字", "四柱八字", "子平", "命書", "日主強弱"]):
            return self._handle_bazi(name)

        # 22. 夢境解析
        elif any(kw in clean_q for kw in ["夢境", "做夢", "夢見", "解夢"]):
            return self._handle_dream(name)

        # 23. 前世因果
        elif any(kw in clean_q for kw in ["前世", "因果", "宿命", "輪迴"]):
            return self._handle_past_life(name)

        # 24. 先天性格與特質
        elif any(kw in clean_q for kw in ["性格", "人生發展", "特質", "個性"]):
            return self._handle_simple(name)

        # 25. 今日錦囊
        elif any(kw in clean_q for kw in ["今日", "每日", "錦囊"]):
            return self._handle_daily(name)

        # 26. 明確指名要求全盤命譜詳評
        elif any(kw in clean_q for kw in ["詳評", "命譜詳評", "格局報告", "全盤詳解", "命盤解析"]):
            return self.generate_report()

        # 27. 全方位人生問事解惑 (兜底保障：具體結合命身宮真實星曜與提問)
        else:
            return self._handle_life_guidance(name, clean_q)

    # =========================================================================
    # 各專案大師開示模組 (Modular Master Handlers)
    # =========================================================================
    def _handle_love(self, name):
        spouse = self._extract_palace("夫妻宮")
        ming = self._extract_palace("命宮")
        fu = self._extract_palace("福德宮")
        
        spouse_main = "、".join(spouse["main_stars"]) if spouse["main_stars"] else "和潤吉曜"
        ming_main = "、".join(ming["main_stars"]) if ming["main_stars"] else "正氣星曜"
        
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "湛藍、象牙白")

        return (
            f"【紫微天機道長 · 桃花情緣錦囊】：\n\n"
            f"緣主 {name} 且聽老道為你撥開情關迷霧！\n"
            f"老道細觀你盤中陰陽造化，你命宮坐守【**{ming_main}**】（底氣 {ming['score']} 分），「夫妻宮」位於地支【{spouse['zhi']}宮】（氣數 **{spouse['score']} 分**），坐守【**{spouse_main}**】，福德情志和合值為 **{fu['score']} 分**。\n\n"
            f"老道特依天地五行相生之理，賜你三大桃花攻略與相處之道：\n\n"
            f"✦ 【第一計：氣場穿搭 · 引動心動同頻】\n"
            f"出門聚會、約會或日常社交時，宜多穿著 **{lucky_color}** 系衣飾或佩帶溫潤飾品。此色能溫和撫平你的剛強氣場，增添柔和親和力，讓他人望之生喜、心生親近。\n\n"
            f"✦ 【第二計：相處心法 · 以柔克剛攻心術】\n"
            f"夫妻宮坐守【{spouse_main}】，顯示你的命中正緣多半為性格獨立、有才華、自尊心強且極重細節之人。\n"
            f"與其相處切記「莫爭口舌之快、莫查隱私瑣事」，宜秉持『相敬如賓、留白相知』之妙法。多在其勞累心煩時，給予一杯溫茶或一句真誠讚賞，最能直擊心坎。\n\n"
            f"✦ 【第三計：天時吉位 · 邂逅良緣之機】\n"
            f"若欲主動結識優質桃花或推進現有感情，請把握每日 **{self.best_timing}**，往你命中的生旺吉方 **{self.best_direction}** 走動，天時地利共振，良緣自會悄然相逢！"
        )

    def _handle_lucky_numbers(self, name):
        import hashlib
        seed_raw = f"{name}{self.user_info.get('birth_date','')}{time.strftime('%Y%m%d')}"
        h = int(hashlib.md5(seed_raw.encode()).hexdigest()[:8], 16)
        lotto_nums = sorted(list(set([(h >> (i*4) ^ (i*7)) % 49 + 1 for i in range(12)]))[:6])
        while len(lotto_nums) < 6: lotto_nums.append((lotto_nums[-1] % 49) + 1)
        c539_nums = sorted(list(set([(h >> (i*3) ^ (i*5)) % 39 + 1 for i in range(10)]))[:5])
        while len(c539_nums) < 5: c539_nums.append((c539_nums[-1] % 39) + 1)
        special_num = (h % 9) + 1

        return (
            f"【紫微天機道長 · 天機乍現財數點撥】：\n\n"
            f"老道凝神觀天象，見紫微垣中財帛流光乍現。特為緣主 {name} 推得今日專屬先天靈動數：\n\n"
            f"✦ 【今日天機特出靈數】：★ **{special_num}** ★\n"
            f"✦ 【大樂透感應六數】：{'、'.join(f'{n:02d}' for n in lotto_nums)}\n"
            f"✦ 【今彩539感應五數】：{'、'.join(f'{n:02d}' for n in c539_nums)}\n\n"
            f"💡 **老道慈悲訓誡**：\n"
            f"天機靈數乃隨今日時空磁場而動，借天地之靈氣以作開運助緣。小賭怡情、積善積福，切勿過度沉迷，厚德方能載物，行善自能聚財！"
        )

    def _handle_past_life(self, name):
        fu = self._extract_palace("福德宮")
        fu_main = "、".join(fu["main_stars"]) if fu["main_stars"] else "清正星曜"
        return (
            f"【天機大師點撥 · 前世宿緣與因果】：\n\n"
            f"老道微閉雙目，神遊太虛，為緣主 {name} 溯源三世福德因果。\n\n"
            f"✦ 【前世宿緣】：觀你福德宮（位於{fu['zhi']}宮，坐守【{fu_main}】）氣象，前世汝乃崇文尚義之文人墨客或醫藥濟世之士，曾結下深厚善緣，亦曾為執著之事殫精竭慮。\n"
            f"✦ 【今生因果】：今生承繼宿世聰慧悟性，故心思敏銳、求知若渴，然偶有心緒起伏、多思易累之感，此乃宿世心念之餘波。\n"
            f"✦ 【今生指引】：多行善事、寬恕放下，心清則慧海生，善用自身才智溫暖周遭，自能修得今生福慧雙圓。"
        )

    def _extract_glyph_char(self, clean_q, prompt=""):
        import re
        full_text = f"{clean_q} {prompt}"
        
        # 1. 優先匹配顯式標記
        markers = [
            r'用戶測字：「([^」]+)」',
            r'測字：「([^」]+)」',
            r'測字：([^\s\n。」]+)',
            r'測字: ([^\s\n。」]+)',
            r'字：([^\s\n。」]+)',
            r'字: ([^\s\n。」]+)',
            r'測「([^」]+)」',
            r'測【([^】]+)】',
            r'測([^字\s\n。]{1,2})字',
            r'卜字：「([^」]+)」',
            r'卜字：([^\s\n。」]+)',
            r'用戶提問：「([^」]+)」',
            r'【緣主提問】：([^\s\n。」]+)',
            r'【提問】：([^\s\n。」]+)'
        ]
        
        for pattern in markers:
            match = re.search(pattern, full_text)
            if match:
                candidate = match.group(1).strip()
                for stop in ["用戶", "提問", "緣主", "大師", "指令", "一個", "字", "請", "幫我", "問", "想", "測"]:
                    candidate = candidate.replace(stop, "")
                if candidate:
                    for ch in candidate:
                        if '\u4e00' <= ch <= '\u9fff':
                            return ch

        # 2. 若無標記，清理常見包裝詞與停用詞後提取第一個漢字
        stop_words = ["用戶", "提問", "緣主", "大師", "指令", "測字", "拆字", "文字占卜", "卜字", "請測", "幫我測", "問事", "測一字", "測", "字", "請", "幫我", "問", "一個", "的", "這個"]
        clean_strip = clean_q.strip()
        for sw in stop_words:
            clean_strip = clean_strip.replace(sw, "")
        clean_strip = clean_strip.strip()
        
        for ch in clean_strip:
            if '\u4e00' <= ch <= '\u9fff':
                return ch
                
        # 3. 備援機制：尋找 prompt 中「測」字或 quotes 附近的漢字
        match = re.search(r'[測「【][^\u4e00-\u9fff]*([\u4e00-\u9fff])', full_text)
        if match:
            return match.group(1)
            
        return "吉"

    def _analyze_character_glyph(self, char):
        """專屬漢字拆字與五行剖析字典引擎"""
        GLYPH_DB = {
            "情": {
                "radicals": "「忄」（豎心旁，主心念與情志） + 「青」（主生機、青春、歲月）",
                "five_elements": "陰陽五行屬【水木相生、心火感應】",
                "meaning": "【情】字左立豎心，右托青藍。心念為情意之起點，右旁「青」字如春草正茂，意謂你當前所懸念的情緣或心境正在萌芽與化育之中。豎心旁亦象徵心中有牽掛、有熱情，然情感波動較大。",
                "advice": "情不宜過急過猛，急則傷心動氣。宜持平常心，少幾分執念，多幾分包容。順應天時氣脈，待歲月沉澱，真情自會水到渠成。",
                "palace_ref": "夫妻宮與福德宮"
            },
            "財": {
                "radicals": "「貝」（古代資財、寶物） + 「才」（才能、智慧、本領）",
                "five_elements": "五行屬【金土生旺、木以立本】",
                "meaning": "【財】字由「貝」與「才」組合而成。貝為財庫與實體資產，才為個人才能與專業智慧。此字明示財富乃隨才能而至，並非憑空妄求。",
                "advice": "求財宜立足專長，穩紮穩打。切忌冒險投機，貝庫需嚴守，廣結善緣自能聚財入庫。",
                "palace_ref": "財帛宮與田宅宮"
            },
            "吉": {
                "radicals": "「士」（君子、賢人） + 「口」（吉慶之言、言語）",
                "five_elements": "五行屬【土金相生、金水相涵】",
                "meaning": "【吉】字上士下口，士為有德君子，口為和氣安祥。此字乃否極泰來、吉星高照之象！預示當前所謀所問之事正向舒展，有貴人相助。",
                "advice": "處事宜持君子之風，修口德、積善緣。逢人多道吉言，祥瑞之氣自然隨身。",
                "palace_ref": "命宮與遷移宮"
            },
            "運": {
                "radicals": "「辶」（辵部，走動遷轉） + 「軍」（陣營、兵馬、實力）",
                "five_elements": "五行屬【水金相生、動中生旺】",
                "meaning": "【運】字帶走字旁（辶），內包「軍」。運者轉動也，暗示現狀宜動不宜過靜。內中「軍」字代表緣主早已備齊實力，唯需突破僵局。",
                "advice": "動則生財，靜則滯礙。宜把握天時大膽開展，向吉方出行交涉，時來運轉即在眼前。",
                "palace_ref": "遷移宮與官祿宮"
            },
            "愛": {
                "radicals": "「爪」（牽繫） + 「冖」（包容庇護） + 「心」（真心） + 「友」（相伴）",
                "five_elements": "五行屬【火土相生、溫潤和合】",
                "meaning": "【愛】字繁體中間有「心」，四方有庇護與攜手之象。暗示當前問事核心在於「體貼與真心」。少一分計較，多一分溫柔包容。",
                "advice": "用心傾聽，溫柔關懷。以誠相待，愛意與善緣自能長青。",
                "palace_ref": "夫妻宮與福德宮"
            },
            "勝": {
                "radicals": "「月」（肉身時月） + 「券/力」（憑證與力量）",
                "five_elements": "五行屬【金木相克、火煉成器】",
                "meaning": "【勝】字起筆有力，左月為根基，右依實力。象徵所問之事競爭劇烈，需歷經一番心血，但最終必能憑藉韌性脫穎而出！",
                "advice": "保持沉著，嚴守紀律。臨陣莫慌，勝利終歸堅忍之人。",
                "palace_ref": "官祿宮與命宮"
            },
            "緣": {
                "radicals": "「纟」（絞絲旁，千絲萬縷） + 「彖」（緣由、卦象）",
                "five_elements": "五行屬【水木相滋、宿世牽繫】",
                "meaning": "【緣】字絞絲旁象徵人與人、人與事之間冥冥中的牽繫。暗示當前遭遇並非偶然，皆是宿世善緣或時空造化之結果。",
                "advice": "隨緣順變，莫強求無理之果。善待眼前人事物，結善緣即是得大福報。",
                "palace_ref": "夫妻宮與奴僕宮"
            },
            "福": {
                "radicals": "「礻」（示字旁，神明祈福） + 「一口田」（衣食無憂、安居）",
                "five_elements": "五行屬【土金相生、福澤深厚】",
                "meaning": "【福】字左為神明垂示，右有一口田。暗示緣主命中自帶福澤，眼前縱有微小波折，亦能受天地暗中庇佑，化險為夷。",
                "advice": "知足常樂，厚德載物。多行善積德，福祿綿延不絕。",
                "palace_ref": "福德宮與田宅宮"
            },
            "安": {
                "radicals": "「宀」（寶蓋頭，家宅房屋） + 「女」（女子安居、平定）",
                "five_elements": "五行屬【土水相和、安居樂業】",
                "meaning": "【安】字屋簷之下有女子安坐，象徵家宅和諧、身心泰然。此字問事主求穩不求急，以安寧、穩健為第一要務。",
                "advice": "靜心修養，穩守本業。莫聽外在喧囂，家安則百事興。",
                "palace_ref": "田宅宮與疾厄宮"
            },
            "平": {
                "radicals": "「干」（盾牌、干戈） + 「丷」（分化、平衡）",
                "five_elements": "五行屬【水木相調、平淡致遠】",
                "meaning": "【平】字字形平衡，兩點分立。象徵風浪漸平、局勢趨於穩定。雖然短期內無狂風暴雨般的爆發，但也無凶險墜落之虞。",
                "advice": "保持平常心，順其自然。平淡之中見真諦，從容面對即是智慧。",
                "palace_ref": "命宮與福德宮"
            },
            "升": {
                "radicals": "「千」（積累） + 「十」（圓滿、升騰）",
                "five_elements": "五行屬【木火通明、步步高陞】",
                "meaning": "【升】字起筆向上，如日方升。問事業主升遷躍進，問財運主節節高升，問學業主金榜題名。乃蓄力已久爆發突破之兆。",
                "advice": "展現自信，勇敢爭取。把握當前契機，順勢登上新台階。",
                "palace_ref": "官祿宮與財帛宮"
            },
            "命": {
                "radicals": "「人」（凡人蒼生） + 「一」（立身之地） + 「口/卩」（受命印信）",
                "five_elements": "五行屬【金木交會、天道運行】",
                "meaning": "【命】字頂天立地，下承印信。問事主「天命與責任」。凡人逢命字，當思考此事的長遠意義，非一時得失衝動。",
                "advice": "修身立命，順應天時。盡人事以聽天命，豁達則無往不利。",
                "palace_ref": "命宮與身宮"
            }
        }
        
        if char in GLYPH_DB:
            return GLYPH_DB[char]
            
        radicals_found = []
        elem = "五行中和"
        
        if any(r in char for r in ["心", "忄", "灬", "火", "日", "光"]):
            radicals_found.append("「心/火部」（主熱情、靈識、情感波動）")
            elem = "陰陽五行屬【火性靈動、意念生發】"
        if any(r in char for r in ["水", "氵", "冫", "雨", "子", "月"]):
            radicals_found.append("「水/月部」（主智慧、潤澤、情感沉澱）")
            elem = "陰陽五行屬【水性溫潤、智慮深遠】"
        if any(r in char for r in ["木", "艸", "艹", "竹", "林", "青"]):
            radicals_found.append("「木/草部」（主生機、蓬勃、成長茁壯）")
            elem = "陰陽五行屬【木性生旺、春意漸濃】"
        if any(r in char for r in ["金", "貝", "刀", "刂", "戈", "玉"]):
            radicals_found.append("「金/寶部」（主決斷、資財、剛健果敢）")
            elem = "陰陽五行屬【金性剛健、利器得展】"
        if any(r in char for r in ["土", "宀", "田", "石", "山", "阜"]):
            radicals_found.append("「土/宅部」（主穩固、包容、基業紮實）")
            elem = "陰陽五行屬【土性厚重、承載萬物】"
        if any(r in char for r in ["人", "亻", "女", "子"]):
            radicals_found.append("「人/女部」（主貴人、情誼、親和互動）")
        if any(r in char for r in ["走", "辶", "行"]):
            radicals_found.append("「走/辵部」（主遷轉、出行、動中求變）")
            
        rad_str = "、".join(radicals_found) if radicals_found else "端正筆畫構造，起落有序"
        
        return {
            "radicals": f"字體結構含 {rad_str}",
            "five_elements": elem,
            "meaning": f"【{char}】字形骨格清晰，起筆端凝，收筆有度。此字象徵當前所問之事初時似有微迷霧，然骨體正大，內蘊後勁與轉化之力。文字脈絡反映緣主此刻內心既有企求亦帶審慎。",
            "advice": "靜觀其變，沉得住氣。堅守本心，順應天時方位，困難自可迎刃而解。",
            "palace_ref": "命宮與福德宮"
        }

    def _handle_glyph(self, name, clean_q, prompt=""):
        char = self._extract_glyph_char(clean_q, prompt)
        info = self._analyze_character_glyph(char)
        
        ming = self._extract_palace("命宮")
        fu = self._extract_palace("福德宮")
        
        return (
            f"【紫微天機道長 · 測字神算破玄機】：\n\n"
            f"緣主 {name} 凝神所卜之字為：「**{char}**」。老道開觀字相、審部首、辨五行氣脈，特為你合參命盤排布：\n\n"
            f"✦ 【一、漢字結構與部首拆解】\n"
            f"- **字形骨架**：{info['radicals']}。\n"
            f"- **五行氣脈**：{info['five_elements']}。\n"
            f"- **拆字寓意**：{info['meaning']}\n\n"
            f"✦ 【二、與緣主命盤宮位感應】\n"
            f"老道觀你命中氣數（命宮底氣 **{ming['score']} 分**、福德情志 **{fu['score']} 分**）：\n"
            f"此「**{char}**」字起筆與你盤中【{info['palace_ref']}】之動能產生微妙共振。字相顯示，當前所問之事表面雖有紛繞或猶豫，然內藏轉機與生機，切莫因一時心亂而自失方寸。\n\n"
            f"✦ 【三、大師指點迷津與開運時空】\n"
            f"- **定心心法**：{info['advice']}\n"
            f"- **天時吉方**：若逢抉擇難定之際，宜選在每日 **{self.best_timing}**，面朝你的生旺吉方【**{self.best_direction}**】靜心深思，吉氣加持，難關自可解開！\n\n"
            f"✦ 【老道定心真言】\n"
            f"『字隨心轉，心正字端。』順應天時氣脈而行，眼前迷霧轉瞬即散，前程必定一片朗然！"
        )

    def _handle_dream(self, name):
        fu = self._extract_palace("福德宮")
        return (
            f"【紫微天機道長 · 夢境玄機開示】：\n\n"
            f"道家云：『神遇為夢，形接為事。』老道觀你福德宮（精神位）氣息（{fu['score']} 分），為你解剖此夢之深層喻義：\n\n"
            f"1. **夢境本質來源**：此夢並非虛妄，乃緣主近期身心負荷或潛意識思慮於夜間歸元時之自然顯化。福德宮吉星閃爍，顯示此夢非凶兆，反有「卸下重擔、迎新除舊」之深意。\n"
            f"2. **心理與氣場投射**：夢中所現之人事物，象徵你在現實中對某項計畫或關係的掛念。夢中若有奔波或波折，正是潛意識在為你排解日常無形壓力。\n"
            f"3. **大師化解與轉運**：夢醒即空，無需罣礙。晨起後飲一杯溫水，面朝【{self.best_direction}】深呼吸三回，將濁氣吐盡，當日運勢必能煥然一新！"
        )

    def _handle_decade(self, name, age):
        ming = self._extract_palace("命宮")
        guan = self._extract_palace("官祿宮")
        decade_start = (age // 10) * 10 + (2 if age % 10 >= 2 else -8)
        decade_end = decade_start + 9
        return (
            f"【紫微天機道長 · 十年大限運程推演】：\n\n"
            f"老道為緣主 {name} 排演大限命宮（當前正值 {decade_start}～{decade_end} 歲十年大運之關鍵樞紐）：\n\n"
            f"1. **大限總體局勢**：此十年大限乃你人生承前啟後之黃金期，命宮底氣 {ming['score']} 分、官祿動能 {guan['score']} 分。氣象由初期的摸索沉澱，逐步走向中後期的主導掌控。\n"
            f"2. **前三年（奠基紮根期）**：重在建立專業威信與厚植人脈資源，切忌急躁冒進，需以守為攻。\n"
            f"3. **中四年（開疆拓土期）**：三方四正吉星匯聚，為此十年運勢最高峰，宜大膽把握升遷、轉型或合夥之良機。\n"
            f"4. **後三年（守成收穫期）**：資產逐步入庫，需注重家庭平衡與健康調養，功成身退、從容自在。\n\n"
            f"💡 **大師提點**：大限之中逢吉化則奮發，逢煞忌則修心。凡事莫逆天時，順應節奏即是福！"
        )

    def _handle_yearly(self, name):
        return (
            f"【紫微天機道長 · 當前流年運勢精批】：\n\n"
            f"老道觀你今年歲君流轉，太歲與天干四化交互引動命盤各宮：\n\n"
            f"1. **歲君主軸與整體氣象**：今年你身心能量充沛，思維敏銳，主動求變之意願強烈。命盤吉星坐照，為開展新計畫或提升生活品質之良年。\n"
            f"2. **事業與財氣動態**：財帛與官祿宮受流年吉曜加持，上半年多播種布局，秋季後有望見到實質收益。若有轉職或拓展副業之念頭，下半年時機更為成熟。\n"
            f"3. **人際情誼與家庭和諧**：人際往來頻繁，能得貴人暗中相助；然偶遇瑣碎摩擦，多寬容包容即可消弭於無形。\n"
            f"4. **歲時避凶提醒**：行車外出注意安全，日常作息宜維持規律，多向你的開運吉方【{self.best_direction}】納氣，自可迎祥納福！"
        )

    def _handle_monthly(self, name):
        return (
            f"【紫微天機道長 · 當前流月吉凶批註】：\n\n"
            f"老道觀你本月月令氣息，特為緣主 {name} 開示三旬進退心法：\n\n"
            f"✦ 【上旬（初一至初十）：蓄勢待發】\n"
            f"月令初始，氣場尚在整理。宜盤點手頭要務，理清輕重緩急，不宜倉促作出重大決策。\n\n"
            f"✦ 【中旬（十一至二十）：乘勢推進】\n"
            f"月令貴人氣運升騰，人際溝通順暢，重要商務拜訪、關鍵談判或提案建議安排於此時期，易獲正面回饋。\n\n"
            f"✦ 【下旬（廿一至月末）：守成收圓】\n"
            f"月尾氣息收斂，宜總結本月所得，避免衝動開銷，多陪伴家人、修養身心，為下一月度積蓄元氣。"
        )

    def _handle_stock(self, name, clean_q=""):
        cai = self._extract_palace("財帛宮")
        guan = self._extract_palace("官祿宮")
        wealth_score = cai["score"]
        career_score = guan["score"]
        
        # 萃取時事輿情多空訊號與技術指標
        bull_weight = 50 + (wealth_score - 50) // 3
        if any(w in clean_q for w in ["利多", "創高", "大漲", "站上線", "偏多", "買超", "獲利", "增", "飆"]):
            bull_weight += 16
        if any(w in clean_q for w in ["利空", "跌破", "重挫", "跌破線", "偏空", "賣超", "衰退", "下修", "弱勢"]):
            bull_weight -= 16
        bull_weight = max(15, min(88, bull_weight))
        
        if bull_weight >= 56:
            trend_tag = "↗ 多方轉強 · 偏多看好"
            pred_range = f"+{round((bull_weight-50)*0.16 + 1.2, 1)}% ~ +{round((bull_weight-50)*0.26 + 3.8, 1)}%"
            tactic = "盤面時事題材熱絡且均線有守，逢回測不破支撐可小量分批佈局，沿短期均線抱牢，嚴守移動停利停損。"
        elif bull_weight <= 44:
            trend_tag = "↘ 空方壓制 · 偏空防守"
            pred_range = f"-{round((50-bull_weight)*0.16 + 1.0, 1)}% ~ -{round((50-bull_weight)*0.25 + 3.2, 1)}%"
            tactic = "時事利空或均線下彎，切勿盲目抄底接飛刀，宜多看少做或逢反彈降低持股水位，現金為王。"
        else:
            trend_tag = "→ 陰陽膠著 · 區間震盪"
            pred_range = "± 1.8% 內狹幅區間整理"
            tactic = "時事消息多空互見，量能尚未明確表態，建議在箱型區間上緣減碼、下緣觀望，靜待方向明朗。"

        return (
            f"【紫微天機道長 · 股市時事與天機氣數三維詳批】：\n\n"
            f"老道以【財經時事輿情】、【盤面技術量能】合參緣主紫微【財帛宮】（氣數 {wealth_score} 分）與【官祿宮】（氣數 {career_score} 分）三維推演：\n\n"
            f"✦ 【一、時事多空與走勢機率預測】：\n"
            f"- **預測趨勢**：★ **{trend_tag}** ★（多頭勝率約 {bull_weight}%）\n"
            f"- **預估波段變動區間**：**{pred_range}**\n"
            f"- **時事風向評析**：市場消息紛擾，真真假假皆為人心之映照。若近期有利多加持，須注意是否有利多出盡之疑；若逢時事利空衝擊，宜檢驗下方強支撐位之承接力道。\n\n"
            f"✦ 【二、技術量能與個人財氣合參】：\n"
            f"- **個人財運磁場**：你目前正財氣象厚實，官祿宮助力穩固。但偏財短線操作重在順應天時與消息脈絡，切忌盲目聽信市場小道消息或追高殺低。\n"
            f"- **關鍵操盤防守**：{tactic}\n\n"
            f"✦ 【三、宗師操盤定心符與出入天時】：\n"
            f"1. **操作紀律**：以時間換取空間，挑選具備長期護城河與時事產業紅利之標的，切莫孤注一擲。\n"
            f"2. **下單吉時吉方**：每日開盤盤初波動劇烈時切莫衝動追單，宜於每日 **{self.best_timing}** 冷靜復盤，面朝 **{self.best_direction}** 沉著定奪。"
        )

    def _handle_omens(self, name):
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "青翠綠、月牙白")
        return (
            f"【紫微天機道長 · 出門吉位與歲時避諱精批】：\n\n"
            f"緣主 {name} 且聽老道為你觀今日天時氣象、演卦定吉凶方位：\n\n"
            f"✦ 【一、今日出門第一大吉位】：★ 喜神大吉向【{self.best_direction}】★\n"
            f"今日出門辦事、赴約商談或出差謀求，宜首選往【{self.best_direction}】啟程迎納祥瑞紫氣。\n"
            f"- **開運穿戴**：出門宜穿戴 **{lucky_color}** 色系衣飾或隨身幸運小物，以五行相生調和自身磁場。\n"
            f"- **出門心法**：出門前靜心三秒，朝吉方跨出第一步，心念祥和，貴人自會逢源相迎。\n\n"
            f"✦ 【二、今日行事最佳吉時】：每日【{self.best_timing}】\n"
            f"此時辰乃今日天時與你命盤最和合之良機。重大洽談、拜訪客戶、簽約定案或關鍵決策，選於此時進行最得天地奧援、事半功倍！\n\n"
            f"✦ 【三、今日歲時禁忌與避諱】：\n"
            f"1. **衝煞方位莫近**：出門辦事切忌急躁往對沖方向奔波；路上遇口角喧鬧之所切莫駐足圍觀，以防沾染雜亂穢氣。\n"
            f"2. **言語處事之忌**：今日忌口出狂言、忌草率承諾。言多必失，多聽少爭，守住口德即是守住福祿財庫。\n"
            f"3. **歸休起居避諱**：日落黃昏後不宜涉足陰暗荒涼之處，入夜宜早歸洗沐靜心，安神固本以蓄明日之元氣。\n\n"
            f"✦ 【四、大師今日護身真言】：\n"
            f"「心正則邪不侵，順時則萬事興。」順應天時方位而行，自可化險為夷、出入平安、吉慶滿堂！"
        )

    def _handle_bazi(self, name):
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        strongest = sorted_elements[-1][0]
        return (
            f"【紫微天機道長 · 正統子平八字詳批】：\n\n"
            f"緣主 {name}，老道為你依四柱八字陰陽五行立命推演：\n\n"
            f"### 一、八字格局與五行強弱\n"
            f"- **日主氣象**：五行造化得天地之中和，命局有情，氣度開闊。\n"
            f"- **五行喜忌**：盤中五行以【{ELEMENT_NAMES[weakest]}】為第一喜用神，最喜相生扶持；以【{ELEMENT_NAMES[strongest]}】為調候梳理之本。\n\n"
            f"### 二、心性特質與內外風範\n"
            f"外圓內方，待人以誠，處事深具韌性。遇難不餒，思慮周全，具有極佳的謀略與領導潛質。\n\n"
            f"### 三、事業財官造化\n"
            f"八字財官相生，功名不求自得。三十歲後逐步大展鴻圖，適合深耕專業技術、經營管理或獨立事業，愈老愈醇厚。\n\n"
            f"### 四、姻緣情感合參\n"
            f"配偶宮坐守喜神，伴侶多具實幹才能。彼此相敬相助，同甘共苦，乃相守一生之福緣。"
        )

    def _handle_simple(self, name):
        ming = self._extract_palace("命宮")
        ming_main = "、".join(ming["main_stars"]) if ming["main_stars"] else "正氣星曜"
        top_p = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)[0]
        return (
            f"【紫微天機道長 · 性格與人生指引】：\n\n"
            f"老道以白話為緣主 {name} 剖析你的先天性情與人生大道：\n\n"
            f"1. **先天人格特質**：你的命宮坐守【**{ming_main}**】（底氣 {ming['score']} 分），外表沉穩謙遜，內心實則有極強的抱負與自尊。你思維縝密，不喜歡虛浮表象，凡事講求實證與邏輯。\n"
            f"2. **人生最核心優勢**：你的最強樞紐在於【**{top_p[0]}**】（{top_p[1]} 分），善於在複雜局面中理清頭緒，找到突破口。只要給你足夠的信任與空間，你便能展現驚人的成果。\n"
            f"3. **此生修練功課**：切忌過度要求完美而讓自己精神內耗。學會接納不完美，凡事盡人事、聽天命，豁達從容，人生必將如行雲流水般順暢！"
        )

    def _handle_daily(self, name):
        return (
            f"【天機大師點撥 · 今日錦囊妙計】：\n\n"
            f"老道為緣主 {name} 觀測今日天時流轉，特賜三條當日開運錦囊：\n\n"
            f"✦ 【錦囊一：出門吉位】：今日大利朝向【{self.best_direction}】，出門行事朝此方啟程，最能迎納祥和吉氣。\n"
            f"✦ 【錦囊二：行事天時】：今日重大決策、重要簽約或關鍵溝通，請鎖定 【{self.best_timing}】，天心呼應，事半功倍。\n"
            f"✦ 【錦囊三：心法箴言】：少言多聽，處事從容，遇事退半步即海闊天空。"
        )

    def _handle_finance(self, name):
        cai = self._extract_palace("財帛宮")
        tian = self._extract_palace("田宅宮")
        cai_main = "、".join(cai["main_stars"]) if cai["main_stars"] else "正財穩健吉曜"
        tian_main = "、".join(tian["main_stars"]) if tian["main_stars"] else "安庫福曜"
        
        return (
            f"【天機大師點撥 · 財運玄機】：\n\n"
            f"老道觀你盤中氣象，緣主 {name} 之「財帛宮」（位於{cai['zhi']}宮，坐守【**{cai_main}**】）氣數評分為 **{cai['score']} 分**，「田宅宮」（坐守【{tian_main}】）庫存指數為 **{tian['score']} 分**。\n\n"
            f"1. **求財路徑直指**：你的財富格局屬於「專業生財、積沙成塔」之相，正財根基紮實。切忌涉足看不懂的高槓桿投機，專心深耕本業衍生之專業領域，財自聚來。\n"
            f"2. **資產守成心法**：田宅宮氣場平穩，日常宜採穩健配置原則，重實質資產儲備，不隨市場短線起伏而亂了心智。\n"
            f"3. **開運天時借力**：若遇重大投資決策或資金規劃，宜選在每日 **{self.best_timing}**，方位宜面朝 **{self.best_direction}**，以引動生旺財氣。"
        )

    def _handle_career(self, name):
        guan = self._extract_palace("官祿宮")
        ming = self._extract_palace("命宮")
        guan_main = "、".join(guan["main_stars"]) if guan["main_stars"] else "事功吉曜"
        ming_main = "、".join(ming["main_stars"]) if ming["main_stars"] else "正氣星曜"
        
        return (
            f"【天機大師點撥 · 事業前程】：\n\n"
            f"老道詳推你命中事功，緣主之「官祿宮」（位於{guan['zhi']}宮，坐守【**{guan_main}**】）氣數為 **{guan['score']} 分**，「命宮」（坐守【{ming_main}】）坐守底氣為 **{ming['score']} 分**。\n\n"
            f"1. **職涯定海神針**：你為人敏銳果決，適合能在專案中獨當一面、具備專業技術或策略主導權之工作，不宜在過度僵化的體制下虛耗光陰。例如現代專業顧問、科技數位、整合企劃等賽道皆大有可為。\n"
            f"2. **晉升與進退時機**：當前時運宜重於「厚積薄發」，先把手頭核心專業做到極致。遇考核或跳槽契機時，主動爭取帶領核心團隊，切莫怯縮。\n"
            f"3. **貴人感應吉方**：你的職場貴人多出現在 **{self.best_direction}** 方位，平時可多向此方向拓展人脈與合作契機。"
        )

    def _handle_health(self, name):
        ji = self._extract_palace("疾厄宮")
        ji_main = "、".join(ji["main_stars"]) if ji["main_stars"] else "本體元神星曜"
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        return (
            f"【天機大師點撥 · 養生防疾】：\n\n"
            f"老道推演五行陰陽盛衰，緣主「疾厄宮」（位於{ji['zhi']}宮，坐守【{ji_main}】）體魄氣分為 **{ji['score']} 分**，五行之中最需溫養者為 **{ELEMENT_NAMES[weakest]}**。\n\n"
            f"1. **臟腑調理關鍵**：五行中【{ELEMENT_NAMES[weakest]}】易受日常勞碌耗損，日常生活中需注意生活作息節律，切莫仗著年輕而長期熬夜。\n"
            f"2. **起居時令箴言**：夜間子丑之時（晚間11點至凌晨3點）正是氣血回流歸元之時，務必安睡休養，給身心充電。\n"
            f"3. **調氣固本指南**：晨間或傍晚宜多步入戶外自然之中，面向 **{self.best_direction}** 進行輕柔伸展或散步，導引天地清和之氣入體。"
        )

    def _handle_villain(self, name):
        nu = self._extract_palace("奴僕宮")
        xiong = self._extract_palace("兄弟宮")
        ming = self._extract_palace("命宮")
        
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")

        return (
            f"【紫微天機道長 · 防小人與化解是非口舌精批】：\n\n"
            f"緣主 {name} 且聽老道為你觀人際氣數、破除暗處是非！\n\n"
            f"老道推演命盤氣息，緣主先天命宮正氣凜然（底氣 {ming['score']} 分），而主掌外在人際與同事之「奴僕宮」氣數為 **{nu['score']} 分**，「兄弟宮」為 **{xiong['score']} 分**。\n"
            f"此象顯示緣主為人仗義耿直、做事認真，然容易「交淺言深、以赤誠待人卻易遭無端嫉妒或背後閒話」。老道特傳你四大辟邪防小人化解秘法：\n\n"
            f"✦ 【第一策：劃定人際邊界 · 杜絕暗箭之隙】\n"
            f"小人最喜借題發揮。職場與社交場合謹記「事上見真章，言上留三分」。不涉足茶水間小圈子是非議論，不向非至交之人透露私人財務與家庭隱私。保持公事公辦、禮貌疏離，小人無柄可執，自然不攻自破。\n\n"
            f"✦ 【第二策：五行磁場護體 · 增強清正正氣】\n"
            f"小人屬陰晦之濁氣，最懼清正之磁場。日常可多穿著或佩戴緣主喜用神 **{lucky_color}** 系列衣飾，五行相生聚氣，能自然形成一層無形護體正氣，使暗處小人望而卻步。\n\n"
            f"✦ 【第三策：風水時空布局 · 青龍壓制白虎】\n"
            f"辦公桌或常用書桌宜遵守「左青龍、右白虎」原則，左手邊物品擺放宜略高於右手邊；桌面可擺放黑曜石或一株常青闊葉植物以阻擋濁氣。遇重要交涉或溝通時，宜面朝你的大吉生旺方位【{self.best_direction}】，心神定則邪不侵。\n\n"
            f"✦ 【第四策：老道贈言 · 破局最高心法】\n"
            f"『君子坦蕩蕩，小人長戚戚。』小人之所以能耗損你，往往是利用了你的情緒。凡事「不隨之起舞、不入其局、冷靜取證」，專注於自身實力精進，你站得越高，小人就越無能為力！"
        )

    def _handle_benefactor(self, name):
        ming = self._extract_palace("命宮")
        qian = self._extract_palace("遷移宮")
        guan = self._extract_palace("官祿宮")
        
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")

        return (
            f"【紫微天機道長 · 招引貴人與人脈通達精批】：\n\n"
            f"緣主 {name} 且聽老道為你推演命中貴人星宿與得道多助之方！\n\n"
            f"老道觀你命盤格局，命宮底氣為 **{ming['score']} 分**，主外在出路與社交機緣之「遷移宮」為 **{qian['score']} 分**，事功之「官祿宮」為 **{guan['score']} 分**。\n"
            f"此象顯示緣主自帶才能，然平時多靠自身硬拼。若欲引動貴人主動提攜，老道賜你三大招貴人心法：\n\n"
            f"✦ 【第一要訣：貴人特徵與出沒之所】\n"
            f"你命中真正的貴人，多為性格沉穩內斂、具備專業權威或年歲稍長於你之長者。其不喜諂媚浮誇，最重人品操守。凡事謙遜請教、言而有信，最易贏得其青睞。\n\n"
            f"✦ 【第二要訣：生旺貴人天時方位】\n"
            f"你的第一貴人吉位位於【{self.best_direction}】。重要商務拜訪、關鍵面試或人脈拓展，宜多往此方位走動。每日最佳貴人感應時辰為 **{self.best_timing}**，借天時相生，極易遇見關鍵引路人。\n\n"
            f"✦ 【第三要訣：氣場穿戴 · 同頻相吸】\n"
            f"出門社交聚會宜多著 **{lucky_color}** 系列衣飾，溫潤自身五行磁場，能消弭外在戾氣，增添親和與信任感。\n\n"
            f"✦ 【老道箴言】：『善結人緣，厚德載福。』常懷感恩利他之心，貴人自然不求自至、常伴左右！"
        )

    def _handle_property(self, name):
        tian = self._extract_palace("田宅宮")
        cai = self._extract_palace("財帛宮")
        tian_main = "、".join(tian["main_stars"]) if tian["main_stars"] else "厚重守成之曜"
        
        return (
            f"【紫微天機道長 · 田宅置產與房產風水精批】：\n\n"
            f"老道為緣主 {name} 推算先天「田宅宮」（位於{tian['zhi']}宮，坐守【{tian_main}】，評分 **{tian['score']} 分**），與「財帛宮」生財動能（評分 **{cai['score']} 分**）：\n\n"
            f"✦ 【一、先天置產格局】：你的田宅氣息穩中求勝，名下宜有實質磚瓦資產作為資產護城河。此生置產宜秉持「量力而行、長期持有、抗通膨為上」，切忌高槓桿炒短線。\n\n"
            f"✦ 【二、購屋置產時機】：田宅宮逢生旺之運，下半年或大運吉星坐守之年最利定奪契約。簽約看屋宜選於每日 **{self.best_timing}**，能保持頭腦清明，避開隱藏瑕疵。\n\n"
            f"✦ 【三、家宅風水吉祥向】：緣主最利向陽納氣之方位為【{self.best_direction}】。大門、客廳窗景或主臥床頭朝此方位，最能引動家肥屋潤、藏風聚氣之福澤！"
        )

    def _handle_exam(self, name):
        guan = self._extract_palace("官祿宮")
        ming = self._extract_palace("命宮")
        return (
            f"【紫微天機道長 · 考運功名與學業升遷精批】：\n\n"
            f"老道觀緣主「官祿宮（學堂位）」文星閃爍（動能 **{guan['score']} 分**），「命宮」悟性為 **{ming['score']} 分**：\n\n"
            f"✦ 【一、先天考運特質】：你思維敏捷、擅長理解融會貫通。然逢大考之際偶有臨場焦慮、思慮過繁之弊。考試關鍵在於「求穩莫求快、先易而後難」。\n\n"
            f"✦ 【二、讀書文昌吉方】：溫書自習時，書桌座位宜面朝【{self.best_direction}】。桌面上保持整潔，可置文竹或四支富貴竹以引動文昌清氣。\n\n"
            f"✦ 【三、臨場定心秘法】：應試當日晨起飲一杯溫水，面朝吉方深呼吸三次定神。每日 **{self.best_timing}** 為你腦力最清明之良辰，重大複習以此時段效率最高！"
        )

    def _handle_travel(self, name):
        qian = self._extract_palace("遷移宮")
        ming = self._extract_palace("命宮")
        qian_main = "、".join(qian["main_stars"]) if qian["main_stars"] else "出外順遂吉曜"
        
        return (
            f"【紫微天機道長 · 出國遠行與異鄉發展精批】：\n\n"
            f"老道推演緣主「遷移宮」外行氣象（位於{qian['zhi']}宮，坐守【{qian_main}】，評分 **{qian['score']} 分**），命宮坐守動能為 **{ming['score']} 分**：\n\n"
            f"✦ 【一、動靜取向】：遷移宮氣象開闊，顯示你命中宜動不宜過靜。出外求學、遠行出差、甚至跨國跨城拓展事業，往往比固守原地更易打開眼界與收穫機緣。\n\n"
            f"✦ 【二、遠行大吉方位】：出外求索或差旅首選方位為【{self.best_direction}】，天時相合，平安利達、順遂如意。\n\n"
            f"✦ 【三、異鄉避險提醒】：出門在外切忌涉足偏僻晦暗之地，財不露白。出發前心念「出入平安」，順應天時方位，定能滿載而歸！"
        )

    def _handle_children(self, name):
        zi = self._extract_palace("子女宮")
        fu = self._extract_palace("福德宮")
        zi_main = "、".join(zi["main_stars"]) if zi["main_stars"] else "聰慧善星"
        
        return (
            f"【紫微天機道長 · 子女緣分與求子育嗣精批】：\n\n"
            f"老道觀緣主「子女宮」（位於{zi['zhi']}宮，坐守【{zi_main}】，評分 **{zi['score']} 分**）與「福德宮」祖蔭厚度（**{fu['score']} 分**）：\n\n"
            f"✦ 【一、子息緣分特質】：子女宮氣度祥和，顯示緣主與後嗣緣分深厚。子女多聰敏獨立，具備自身主見與造化，成年後多能自立門戶。\n\n"
            f"✦ 【二、教養相處之道】：與子女相處宜重於「言傳身教、多引導少苛責」。多傾聽其心聲，給予探索空間，福澤自會綿延後代。\n\n"
            f"✦ 【三、備孕求嗣福方】：求嗣講究陰陽和順。調養身體切莫急躁，心平氣和、積德行善，每日宜朝【{self.best_direction}】納氣靜坐，瓜熟自會蒂落！"
        )

    def _handle_marriage(self, name):
        spouse = self._extract_palace("夫妻宮")
        fu = self._extract_palace("福德宮")
        spouse_main = "、".join(spouse["main_stars"]) if spouse["main_stars"] else "和睦吉星"
        
        return (
            f"【紫微天機道長 · 婚姻和諧與白頭偕老精批】：\n\n"
            f"老道觀緣主「夫妻宮」（位於{spouse['zhi']}宮，坐守【{spouse_main}】，共振氣數 **{spouse['score']} 分**）與「福德宮」情志（**{fu['score']} 分**）：\n\n"
            f"✦ 【一、婚姻本質】：天下夫妻皆是前世修來的緣分。盤中顯示伴侶性格多有其堅持與自尊，兩人相處最忌「爭口舌高低、翻陳年舊帳」。\n\n"
            f"✦ 【二、化解摩擦妙法】：逢分歧時，切記「先處理情緒，再處理事情」。遇爭執先退半步，少一句氣話，多一句體諒，家宅自然祥和。\n\n"
            f"✦ 【三、防範外緣侵擾】：臥室床頭宜端正靠實牆，可朝向【{self.best_direction}】安神納吉。彼此坦誠信任，任何外在波折皆難以動搖真情基石！"
        )

    def _handle_luck_transformation(self, name):
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")
        return (
            f"【紫微天機道長 · 開運轉運與化解厄運秘法】：\n\n"
            f"老道為緣主 {name} 推演周天五行盛衰，特傳道家辟邪轉運三部曲：\n\n"
            f"✦ 【第一步：除舊布新 · 淨化濁氣】\n"
            f"凡運勢低迷或犯太歲時，晨起以溫鹽水洗沐面部與雙手，洗淨身心塵垢。將居所玄關與床鋪周遭打掃一空，除舊方能迎新。\n\n"
            f"✦ 【第二步：五行相生 · 聚引祥和】\n"
            f"你命中五行最喜【{ELEMENT_NAMES[weakest]}】，日常多穿著 **{lucky_color}** 系衣物，佩帶溫潤開運物，借天地之氣滋養自身命局。\n\n"
            f"✦ 【第三步：朝向吉方 · 借力天地】\n"
            f"每日清晨可於 **{self.best_timing}**，向著生旺大吉方【{self.best_direction}】深深呼吸三回，心念「天道酬善，否極泰來」，厄運自會散去，福祿自來！"
        )

    def _handle_parents(self, name):
        fu_mu = self._extract_palace("父母宮")
        fu_mu_main = "、".join(fu_mu["main_stars"]) if fu_mu["main_stars"] else "祖德庇蔭吉曜"
        return (
            f"【紫微天機道長 · 父母長輩與孝親福報精批】：\n\n"
            f"老道為緣主推演「父母宮」（位於{fu_mu['zhi']}宮，坐守【{fu_mu_main}】，氣數 **{fu_mu['score']} 分**）：\n\n"
            f"✦ 【一、父母緣分】：父母宮得吉曜庇蔭，長輩對你多懷關愛與期許。唯長輩觀念偶有傳統固執之處，相處宜以順承溫和為重。\n\n"
            f"✦ 【二、孝親得大福報】：百善孝為先。凡對長輩敬順體貼之人，自身運勢往往受祖蔭暗中相助，常能逢凶化吉。\n\n"
            f"✦ 【三、長輩健康祈福】：日常宜多關心長輩睡眠作息與關節筋骨，逢年過節可面朝【{self.best_direction}】為雙親祈願安康，自聚滿門吉慶！"
        )

    def _handle_life_guidance(self, name, clean_q=""):
        ming = self._extract_palace("命宮")
        body_palace_name = self._get_body_palace()
        body = self._extract_palace(body_palace_name)
        top_p = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)[0]
        weak_p = sorted(self.palace_scores.items(), key=lambda x: x[1])[0]
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")
        
        ming_main = "、".join(ming["main_stars"]) if ming["main_stars"] else "正氣星曜"

        return (
            f"【紫微天機道長 · 乾坤問津人生解惑】：\n\n"
            f"緣主 {name} 且平心靜氣，聽老道為你觀照當前心境、指點迷津！\n\n"
            f"世事如棋局局新，凡人逢困頓或抉擇時，心亂則神移。老道觀你命宮坐守【**{ming_main}**】（底氣 **{ming['score']} 分**），身宮寄託於【**{body_palace_name}**】：\n\n"
            f"✦ 【一、觀照根基 · 命中有大福澤】\n"
            f"你命盤中最強的福澤樞紐在於【**{top_p[0]}**】（底氣 **{top_p[1]} 分**），這代表你先天具備極強的生機與翻盤潛質！眼前之波折迷惘，不過是行至【**{weak_p[0]}**】時的暫時磨礪，絕非終局。\n\n"
            f"✦ 【二、大師指路 · 破除當前執念】\n"
            f"針對你心中所念之事，謹記「急則生亂，緩則圓通」。眼前若有猶豫不決之事，莫要逼迫自己在混亂中做重大決定。給自己三至七日靜沉心緒，多聽少動，待局勢明朗後再行定奪。\n\n"
            f"✦ 【三、借天時時空轉運】\n"
            f"每日可於 **{self.best_timing}**，面朝你的生旺吉方【**{self.best_direction}**】散步或深思；身著 **{lucky_color}** 系衣飾調和磁場，自能生出澄澈智慧。\n\n"
            f"✦ 【老道定心真言】\n"
            f"『山重水複疑無路，柳暗花明又一村。』天生我材必有用，順應天時而行，眼前迷霧轉瞬即散，前程定是一片開闊！"
        )


def solve_fate_cpsat(chart_data, user_info, prompt="", target_type="chat"):
    """執行求解並返回大師開示結果"""
    solver = FateCPSATSolver(chart_data=chart_data, user_info=user_info, prompt=prompt)
    solver.solve()
    return solver.answer_query(prompt, target_type=target_type)


def stream_cpsat_ai(prompt, system_prompt="", chart_data=None, user_info=None, target_type="chat"):
    """
    大師口吻之串流生成器
    """
    solver = FateCPSATSolver(chart_data=chart_data, user_info=user_info, prompt=prompt)
    
    success = solver.solve()
    if not success:
        solver.build_model()
        success = solver.solve(time_limit_seconds=1.5)
    
    # 判斷是否為章節解讀提問
    if "章節：" in prompt and "包含規則：" in prompt:
        yield f"### 💡 【大師章節深入批註】：\n"
        yield f"老道綜觀此章節之神煞排布，吉星拱照有情，煞星亦有相應宮位化解阻尼。\n"
        yield f"命中凡遇考驗皆是造化成全，只要循序漸進、動靜相宜，自然能逢凶化吉、履險如夷！\n\n"
        return

    # 判斷是否為最終總結提問
    if "天機判語 · 命理終極總結" in prompt or "請做最後的總結與建議" in prompt:
        yield f"【天機道長 · 終極格局提點】：\n\n"
        yield f"老道為你總覽全盤氣數，骨格清奇，器宇不凡。\n"
        yield f"此生行事當以『積健為雄、順天應人』為要領。多借用你的喜用神【{ELEMENT_NAMES.get(list(solver.element_scores.keys())[0], '木')}】之生機，"
        yield f"逢每日 {solver.best_timing} 之天時，坐臥 {solver.best_direction} 之吉地，凡事從容定奪，前路必定一片豁朗！\n"
        return

    # 一般提問、專項指引或完整命譜
    if target_type in ['love', 'finance', 'pastLife', 'daily', 'career', 'health', 'bazi', 'stock', 'chat'] or prompt:
        ans = solver.answer_query(prompt, target_type=target_type)
        for chunk in ans.split("\n\n"):
            yield chunk + "\n\n"
            time.sleep(0.02)
    else:
        full_report = solver.generate_report()
        for chunk in full_report.split("\n\n"):
            yield chunk + "\n\n"
            time.sleep(0.02)
