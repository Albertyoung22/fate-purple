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
    "紫微": {"base": 22, "elem": "earth", "trait": "帝王之尊，統禦全域，具領袖開創格局"},
    "天府": {"base": 20, "elem": "earth", "trait": "南斗令星，庫存充盈，善理財守成與企劃"},
    "太陽": {"base": 18, "elem": "fire", "trait": "光芒普照，博愛仗義，利名聲與遠方拓展"},
    "太陰": {"base": 18, "elem": "water", "trait": "月曜清澄，心思縝密，主富厚與策劃深謀"},
    "武曲": {"base": 20, "elem": "metal", "trait": "正財星宿，剛毅果決，善財務決策與執行"},
    "天同": {"base": 15, "elem": "water", "trait": "福德之星，溫柔敦厚，貴人運隆，重生活情調"},
    "廉貞": {"base": 17, "elem": "fire", "trait": "次桃花與事業雄心，公關交際強，具政治直覺"},
    "天機": {"base": 17, "elem": "wood", "trait": "智慧謀略，應變神速，擅策略分析與數理推演"},
    "貪狼": {"base": 16, "elem": "wood", "trait": "第一桃花與才藝之曜，靈活多變，喜創投突破"},
    "巨門": {"base": 14, "elem": "water", "trait": "是非與辯才之星，心思深邃，利法律諮詢演說"},
    "天相": {"base": 16, "elem": "water", "trait": "宰相印璽，輔佐周全，重誠信契約與人脈協同"},
    "天梁": {"base": 17, "elem": "earth", "trait": "蔭星壽相，老成持重，逢凶化吉，具監察風骨"},
    "七殺": {"base": 16, "elem": "metal", "trait": "將星威權，獨當一面，敢闖敢拼，利開拓先鋒"},
    "破軍": {"base": 15, "elem": "water", "trait": "破耗先驅，破舊立新，勇於革新變革，不畏艱難"}
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

    def generate_report(self):
        """完整命譜最優化推演解析報告（大師開示）"""
        if not self.solved:
            return "【大師感應】：天機玄妙，星曜交錯產生相斥之氣，請重新校驗生辰與命盤配置。"

        age = self.user_info.get("age", 30)
        name = self.user_info.get("user_name", "緣主")
        zodiac = self.user_info.get("zodiac", "吉瑞")
        
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

    def answer_query(self, prompt, target_type="chat"):
        """根據緣主提問，由大師口吻給予精準具體指引"""
        if not self.solved:
            self.solve()
            
        p_lower = prompt.lower()
        age = self.user_info.get("age", 30)
        name = self.user_info.get("user_name", "緣主")
        
        # 精準提取用戶真實提問，徹底隔離背景命盤資訊 (避免背景命盤包含的八字、財帛宮等關鍵字干擾)
        clean_q = prompt
        if "--------------------------------------------------" in prompt:
            clean_q = prompt.split("--------------------------------------------------")[-1]
        elif "【緣主提問】" in prompt:
            clean_q = prompt.split("【緣主提問】")[-1]
        elif "【緣主祈求】" in prompt:
            clean_q = prompt.split("【緣主祈求】")[-1]
        elif "【大師指令】" in prompt:
            clean_q = prompt.split("【大師指令】")[-1]
        elif "【指令】" in prompt:
            clean_q = prompt.split("【指令】")[-1]
        elif "請詳細分析" in prompt:
            clean_q = prompt.split("請詳細分析")[-1]
        elif "\n\n" in prompt:
            paras = [p for p in prompt.split("\n\n") if p.strip()]
            clean_q = paras[-1]

        # 1. 桃花攻略與感情姻緣
        if target_type == "love" or any(kw in clean_q for kw in ["桃花", "感情", "婚姻", "夫妻", "另一半", "對象", "姻緣", "脫單", "復合", "伴侶", "情緣"]):
            score = self.palace_scores.get("夫妻宮", 58)
            karma_score = self.palace_scores.get("福德宮", 66)
            life_score = self.palace_scores.get("命宮", 76)
            
            spouse_stars = []
            life_stars = []
            for p in self.chart_data:
                p_name = p.get("palaceName", "")
                stars = p.get("stars", [])
                for s in stars:
                    s_name = s.get("name", "") if isinstance(s, dict) else str(s)
                    clean_s = s_name.split(" ")[0].split("(")[0]
                    if "夫妻" in p_name:
                        spouse_stars.append(clean_s)
                    elif "命" in p_name:
                        life_stars.append(clean_s)
                        
            spouse_str = "、".join(spouse_stars) if spouse_stars else "和潤吉曜"
            life_str = "、".join(life_stars) if life_stars else "紫微正曜"
            lucky_color = ELEMENT_COLORS.get("water", "湛藍、象牙白")

            return (
                f"【紫微天機道長 · 桃花情緣錦囊】：\n\n"
                f"緣主 {name} 且聽老道為你撥開情關迷霧！\n"
                f"老道細觀你盤中陰陽造化，你命宮坐守【{life_str}】（底氣 {life_score} 分），「夫妻宮」共振氣數為 **{score} 分**，「福德宮」情志和合值為 **{karma_score} 分**，夫妻宮坐守【{spouse_str}】。\n\n"
                f"你盤中紅鸞星動、暗香浮動，老道特依天地五行相生之理，賜你三大桃花攻略與相處之道：\n\n"
                f"✦ 【第一計：氣場穿搭 · 引動心動同頻】\n"
                f"你命中五行相生最喜生旺，出門聚會、約會或日常社交時，宜多穿著 **{lucky_color}** 系之衣物或佩帶溫潤飾品。此色能溫和撫平你的剛強氣場，增添柔和親和力，讓他人望之生喜、心生親近。\n\n"
                f"✦ 【第二計：相處心法 · 以柔克剛攻心術】\n"
                f"夫妻宮坐【{spouse_str}】，顯示你的命中正緣多半為性格獨立、有才華、自尊心強且極重細節之人。\n"
                f"與其相處切記「莫爭口舌之快、莫查隱私瑣事」，宜秉持『相敬如賓、留白相知』之妙法。多在其勞累心煩時，給予一杯溫茶或一句真誠讚賞，最能直擊心坎。\n\n"
                f"✦ 【第三計：天時吉位 · 邂逅良緣之機】\n"
                f"若欲主動結識優質桃花或推進現有感情，請把握每日 **{self.best_timing}**，往你命中的生旺吉方 **{self.best_direction}**（如該方位之雅緻咖啡廳、藝文展覽或景觀綠地）走動，天時地利共振，良緣自會悄然相逢！"
            )

        # 2. 幸運號碼與偏財靈動數
        elif any(kw in clean_q for kw in ["號碼", "樂透", "威力彩", "539", "幸運號", "彩券", "偏財"]):
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

        # 3. 前世因果
        elif target_type == "pastLife" or any(kw in clean_q for kw in ["前世", "因果", "宿命", "輪迴"]):
            karma_score = self.palace_scores.get("福德宮", 65)
            life_score = self.palace_scores.get("命宮", 75)
            return (
                f"【天機大師點撥 · 前世宿緣與因果】：\n\n"
                f"老道微閉雙目，神遊太虛，為緣主 {name} 溯源三世福德因果。\n\n"
                f"✦ 【前世宿緣】：觀你福德宮氣象，前世汝乃崇文尚義之文人墨客或醫藥濟世之士，曾結下深厚善緣，亦曾為執著之事殫精竭慮。\n"
                f"✦ 【今生因果】：今生承繼宿世聰慧悟性，故心思敏銳、求知若渴，然偶有心緒起伏、多思易累之感，此乃宿世心念之餘波。\n"
                f"✦ 【今生指引】：多行善事、寬恕放下，心清則慧海生，善用自身才智溫暖周遭，自能修得今生福慧雙圓。"
            )

        # 4. 測字占卜
        elif target_type == "glyph" or any(kw in clean_q for kw in ["測字", "漢字", "文字占卜"]):
            char = "吉"
            for marker in ["用戶測字：「", "測字：「", "測字: ", "字：", "字:"]:
                if marker in clean_q:
                    part = clean_q.split(marker)[-1]
                    for end in ["」", "」", "。", " ", "\n"]:
                        if end in part: part = part.split(end)[0]
                    if part: char = part.strip()[:2]; break

            return (
                f"【紫微天機道長 · 測字神算破玄機】：\n\n"
                f"緣主所卜之字為：「**{char}**」。老道凝神觀字相、審形體、辨五行生剋：\n\n"
                f"1. **字形骨架解析**：字如其人，亦如其事。「{char}」字起筆端凝，收筆有度，象徵當前所問之事初時似有迷霧，然骨格端正，內藏生機。\n"
                f"2. **五行陰陽剖析**：此字氣息與你的命宮氣場互為感應，顯示所謀之事關鍵在於『沉得住氣、靜待時機』，切莫操之過急。\n"
                f"3. **大師一語斷吉凶**：事有轉機，貴人將至！眼前若有猶豫不決之處，順其自然、堅守本心，不出百日必見柳暗花明之喜！"
            )

        # 5. 夢境解析
        elif target_type == "dream" or any(kw in clean_q for kw in ["夢境", "做夢", "夢見", "解夢"]):
            karma_score = self.palace_scores.get("福德宮", 65)
            return (
                f"【紫微天機道長 · 夢境玄機開示】：\n\n"
                f"道家云：『神遇為夢，形接為事。』老道觀你福德宮（精神位）氣息（{karma_score} 分），為你解剖此夢之深層喻義：\n\n"
                f"1. **夢境本質來源**：此夢並非虛妄，乃緣主近期身心負荷或潛意識思慮於夜間歸元時之自然顯化。福德宮吉星閃爍，顯示此夢非凶兆，反有「卸下重擔、迎新除舊」之深意。\n"
                f"2. **心理與氣場投射**：夢中所現之人事物，象徵你在現實中對某項計畫或關係的掛念。夢中若有奔波或波折，正是潛意識在為你排解日常無形壓力。\n"
                f"3. **大師化解與轉運**：夢醒即空，無需罣礙。晨起後飲一杯溫水，面朝【{self.best_direction}】深呼吸三回，將濁氣吐盡，當日運勢必能煥然一新！"
            )

        # 6. 十年大限運程推演
        elif any(kw in clean_q for kw in ["大限", "十年", "大運", "十年運程"]):
            life_score = self.palace_scores.get("命宮", 75)
            career_score = self.palace_scores.get("官祿宮", 65)
            decade_start = (age // 10) * 10 + (2 if age % 10 >= 2 else -8)
            decade_end = decade_start + 9
            return (
                f"【紫微天機道長 · 十年大限運程推演】：\n\n"
                f"老道為緣主 {name} 排演大限命宮（當前正值 {decade_start}～{decade_end} 歲十年大運之關鍵樞紐）：\n\n"
                f"1. **大限總體局勢**：此十年大限乃你人生承前啟後之黃金期，命宮底氣 {life_score} 分、官祿動能 {career_score} 分。氣象由初期的摸索沉澱，逐步走向中後期的主導掌控。\n"
                f"2. **前三年（奠基紮根期）**：重在建立專業威信與厚植人脈資源，切忌急躁冒進，需以守為攻。\n"
                f"3. **中四年（開疆拓土期）**：三方四正吉星匯聚，為此十年運勢最高峰，宜大膽把握升遷、轉型或合夥之良機。\n"
                f"4. **後三年（守成收穫期）**：資產逐步入庫，需注重家庭平衡與健康調養，功成身退、從容自在。\n\n"
                f"💡 **大師提點**：大限之中逢吉化則奮發，逢煞忌則修心。凡事莫逆天時，順應節奏即是福！"
            )

        # 7. 流年運勢
        elif any(kw in clean_q for kw in ["流年", "今年", "歲運", "年運"]):
            return (
                f"【紫微天機道長 · 當前流年運勢精批】：\n\n"
                f"老道觀你今年歲君流轉，太歲與天干四化交互引動命盤各宮：\n\n"
                f"1. **歲君主軸與整體氣象**：今年你身心能量充沛，思維敏銳，主動求變之意願強烈。命盤吉星坐照，為開展新計畫或提升生活品質之良年。\n"
                f"2. **事業與財氣動態**：財帛與官祿宮受流年吉曜加持，上半年多播種布局，秋季後有望見到實質收益。若有轉職或拓展副業之念頭，下半年時機更為成熟。\n"
                f"3. **人際情誼與家庭和諧**：人際往來頻繁，能得貴人暗中相助；然偶遇瑣碎摩擦，多寬容包容即可消弭於無形。\n"
                f"4. **歲時避凶提醒**：行車外出注意安全，日常作息宜維持規律，多向你的開運吉方【{self.best_direction}】納氣，自可迎祥納福！"
            )

        # 8. 流月運勢
        elif any(kw in clean_q for kw in ["流月", "本月", "月令", "月運"]):
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

        # 9. 股市天機
        elif target_type == "stock" or any(kw in clean_q for kw in ["股票", "股價", "股市", "大盤", "個股", "代號"]):
            wealth_score = self.palace_scores.get("財帛宮", 65)
            career_score = self.palace_scores.get("官祿宮", 65)
            return (
                f"【紫微天機道長 · 股市天機氣數合參】：\n\n"
                f"老道以紫微【財帛宮】（氣數 {wealth_score} 分）與【官祿宮】（氣數 {career_score} 分），合參當前市場情緒與標的氣象：\n\n"
                f"1. **盤勢磁場與個人財氣**：你目前正財磁場厚實，偏財則重在波段把握。若欲操作股票標的，切忌盲目聽信市場小道消息或追高殺低。\n"
                f"2. **操作節奏定心符**：宜採『分批布局、逢低分批吸納、嚴設停損』之紀律。以時間換取空間，挑選具備長期護城河與基本面支撐之標的為上策。\n"
                f"3. **出入天時禁忌**：每日開盤盤初波動劇烈之時切莫衝動追單，宜於每日 **{self.best_timing}** 冷靜分析復盤，面朝 **{self.best_direction}** 沉著定奪。"
            )

        # 10. 今日出門吉位與歲時避諱精批
        elif any(kw in clean_q for kw in ["出門吉位", "吉位", "避諱", "歲時禁忌", "歲時避諱", "歲時", "出行"]):
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

        # 11. 子平八字命書
        elif target_type == "bazi" or any(kw in clean_q for kw in ["八字詳批", "子平八字", "四柱八字", "子平", "命書", "日主強弱"]):
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

        # 12. 先天性格與人生發展
        elif target_type == "simple" or any(kw in clean_q for kw in ["性格", "人生發展", "特質"]):
            life_score = self.palace_scores.get("命宮", 76)
            top_p = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)[0]
            return (
                f"【紫微天機道長 · 性格與人生指引】：\n\n"
                f"老道以白話為緣主 {name} 剖析你的先天性情與人生大道：\n\n"
                f"1. **先天人格特質**：你的命宮底氣充沛（{life_score} 分），外表沉穩謙遜，內心實則有極強的抱負與自尊。你思維縝密，不喜歡虛浮表象，凡事講求實證與邏輯。\n"
                f"2. **人生最核心優勢**：你的最強樞紐在於【{top_p[0]}】（{top_p[1]} 分），善於在複雜局面中理清頭緒，找到突破口。只要給你足夠的信任與空間，你便能展現驚人的成果。\n"
                f"3. **此生修練功課**：切忌過度要求完美而讓自己精神內耗。學會接納不完美，凡事盡人事、聽天命，豁達從容，人生必將如行雲流水般順暢！"
            )

        # 13. 今日錦囊妙計
        elif target_type == "daily" or any(kw in clean_q for kw in ["今日", "每日", "錦囊"]):
            return (
                f"【天機大師點撥 · 今日錦囊妙計】：\n\n"
                f"老道為緣主 {name} 觀測今日天時流轉，特賜三條當日開運錦囊：\n\n"
                f"✦ 【錦囊一：出門吉位】：今日大利朝向【{self.best_direction}】，出門行事朝此方啟程，最能迎納祥和吉氣。\n"
                f"✦ 【錦囊二：行事天時】：今日重大決策、重要簽約或關鍵溝通，請鎖定 【{self.best_timing}】，天心呼應，事半功倍。\n"
                f"✦ 【錦囊三：心法箴言】：少言多聽，處事從容，遇事退半步即海闊天空。"
            )

        # 13. 財運與投資
        elif target_type == "finance" or any(kw in clean_q for kw in ["財", "錢", "投資", "理財", "發財", "財帛"]):
            score = self.palace_scores.get("財帛宮", 65)
            prop_score = self.palace_scores.get("田宅宮", 60)
            return (
                f"【天機大師點撥 · 財運玄機】：\n\n"
                f"老道觀你盤中氣象，緣主 {name} 之「財帛宮」氣數評分為 **{score} 分**，「田宅宮」庫存指數為 **{prop_score} 分**。\n\n"
                f"1. **求財路徑直指**：你的財富格局屬於「專業生財、積沙成塔」之相，正財根基紮實。切忌涉足看不懂的高槓桿投機，專心深耕本業衍生之專業領域，財自聚來。\n"
                f"2. **資產守成心法**：田宅宮氣場平穩，日常宜採穩健配置原則，重實質資產儲備，不隨市場短線起伏而亂了心智。\n"
                f"3. **開運天時借力**：若遇重大投資決策或資金規劃，宜選在每日 **{self.best_timing}**，方位宜面朝 **{self.best_direction}**，以引動生旺財氣。"
            )

        # 14. 事業與職涯
        elif any(kw in clean_q for kw in ["工作", "事業", "職業", "升遷", "跳槽", "創業", "官祿"]):
            score = self.palace_scores.get("官祿宮", 65)
            life_score = self.palace_scores.get("命宮", 70)
            return (
                f"【天機大師點撥 · 事業前程】：\n\n"
                f"老道詳推你命中事功，緣主之「官祿宮」氣數為 **{score} 分**，「命宮」坐守底氣為 **{life_score} 分**。\n\n"
                f"1. **職涯定海神針**：你為人敏銳果決，適合能在專案中獨當一面、具備專業技術或策略主導權之工作，不宜在過度僵化的體制下虛耗光陰。例如現代專業顧問、科技數位、整合企劃等賽道皆大有可為。\n"
                f"2. **晉升與進退時機**：當前時運宜重於「厚積薄發」，先把手頭核心專業做到極致。遇考核或跳槽契機時，主動爭取帶領核心團隊，切莫怯縮。\n"
                f"3. **貴人感應吉方**：你的職場貴人多出現在 **{self.best_direction}** 方位，平時可多向此方向拓展人脈與合作契機。"
            )

        # 15. 健康與疾厄
        elif any(kw in clean_q for kw in ["健康", "疾厄", "身體", "作息", "疾病"]):
            score = self.palace_scores.get("疾厄宮", 50)
            sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
            weakest = sorted_elements[0][0]
            return (
                f"【天機大師點撥 · 養生防疾】：\n\n"
                f"老道推演五行陰陽盛衰，緣主「疾厄宮」體魄氣分為 **{score} 分**，五行之中最需溫養者為 **{ELEMENT_NAMES[weakest]}**。\n\n"
                f"1. **臟腑調理關鍵**：五行中【{ELEMENT_NAMES[weakest]}】易受日常勞碌耗損，日常生活中需注意生活作息節律，切莫仗著年輕而長期熬夜。\n"
                f"2. **起居時令箴言**：夜間子丑之時（晚間11點至凌晨3點）正是氣血回流歸元之時，務必安睡休養，給身心充電。\n"
                f"3. **調氣固本指南**：晨間或傍晚宜多步入戶外自然之中，面向 **{self.best_direction}** 進行輕柔伸展或散步，導引天地清和之氣入體。"
            )

        # 16. 預設：完整命譜詳評
        else:
            return self.generate_report()


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
    
    yield "【紫微天機道長 · 閉目凝神，推演乾坤...】\n"
    yield "老道正依先天紫微斗數，排布十二宮度神煞，調和五行生剋之氣數...\n"
    time.sleep(0.04)
    
    success = solver.solve()
    if not success:
        yield "天機稍起微瀾，老道稍作調息，再次聚氣定盤...\n"
        solver.build_model()
        success = solver.solve(time_limit_seconds=1.5)
    
    yield "天機顯現，吉凶明朗，緣主且靜聽老道為你細細道來：\n\n"
    time.sleep(0.04)
    
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

