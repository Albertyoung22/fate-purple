import json
import logging
import re

# --- Data Structures & Constants ---

PALACE_NAMES = {
    "life": "命宮", 
    "siblings": "兄弟宮", 
    "spouse": "夫妻宮", 
    "kids": "子女宮", 
    "wealth": "財帛宮", 
    "health": "疾厄宮", 
    "travel": "遷移宮", 
    "friends": "奴僕宮", 
    "career": "官祿宮", 
    "property": "田宅宮", 
    "fortune": "福德宮", 
    "parents": "父母宮"
}

PALACE_ORDER = [
    "life", "siblings", "spouse", "kids", "wealth", "health", 
    "travel", "friends", "career", "property", "fortune", "parents"
]

STAR_MAP = {
    # 14 Major
    "zi_wei": "紫微", "tian_ji": "天機", "tai_yang": "太陽", "wu_qu": "武曲", 
    "tian_tong": "天同", "lian_zhen": "廉貞", "tian_fu": "天府", "tai_yin": "太陰", 
    "tan_lang": "貪狼", "ju_men": "巨門", "tian_xiang": "天相", "tian_liang": "天梁", 
    "qi_sha": "七殺", "po_jun": "破軍",
    # 6 Lucky
    "zuo_fu": "左輔", "you_bi": "右弼", "tian_kui": "天魁", "tian_yue": "天鉞", 
    "wen_chang": "文昌", "wen_qu": "文曲",
    # 6 Sha
    "qing_yang": "擎羊", "tuo_luo": "陀羅", "huo_xing": "火星", "ling_xing": "鈴星", 
    "di_kong": "地空", "di_jie": "地劫",
    # Others
    "lu_cun": "祿存", "tian_ma": "天馬", 
    "hong_luan": "紅鸞", "tian_xi": "天喜", 
    "tian_yao": "天姚", "tian_xing": "天刑", "yin_sha": "陰煞",
    "long_chi": "龍池", "feng_ge": "鳳閣",
    "li_shi": "力士",
    "tian_ku": "天哭",
    "tian_xu": "天虛",
    "gu_chen": "孤辰",
    "gua_su": "寡宿",
    "xian_chi": "咸池",
    "mu_yu": "沐浴",
    "san_tai": "三台",
    "ba_zuo": "八座",
    "tian_cai": "天才",
    "tian_shou": "天壽",
    "tian_wu": "天巫",
    "guan_fu": "官符",
    "bing_fu": "病符",
    "da_hao": "大耗",
    "tian_yve_2": "天月",
    "po_sui": "破碎",
    # 12 Life Stages (Chang Sheng)
    "chang_sheng": "長生", "mu_yu": "沐浴", "guan_dai": "冠帶", "ling_guan": "臨官", 
    "di_wang": "帝旺", "shuai": "衰", "bing": "病", "si": "死", 
    "mu": "墓", "jue": "絕", "tai": "胎", "yang": "養",
    "tian_kong": "天空",
    "tian_gwan": "天官",
    "tian_fu_2": "天福",
    "jie_shen": "解神",
    "tai_fu": "台輔",
    "feng_诰": "封誥",
    "en_guang": "恩光",
    "tian_gui": "天貴",

}

TRANSFORMATION_MAP = {
    "hua_lu": "化祿",
    "hua_quan": "化權",
    "hua_ke": "化科",
    "hua_ji": "化忌"
}

SI_HUA_TABLE = {
    "甲": {"hua_lu": "lian_zhen", "hua_quan": "po_jun", "hua_ke": "wu_qu", "hua_ji": "tai_yang"},
    "乙": {"hua_lu": "tian_ji", "hua_quan": "tian_liang", "hua_ke": "zi_wei", "hua_ji": "tai_yin"},
    "丙": {"hua_lu": "tian_tong", "hua_quan": "tian_ji", "hua_ke": "wen_chang", "hua_ji": "lian_zhen"},
    "丁": {"hua_lu": "tai_yin", "hua_quan": "tian_tong", "hua_ke": "tian_ji", "hua_ji": "ju_men"},
    "戊": {"hua_lu": "tan_lang", "hua_quan": "tai_yin", "hua_ke": "you_bi", "hua_ji": "tian_ji"},
    "己": {"hua_lu": "wu_qu", "hua_quan": "tan_lang", "hua_ke": "tian_liang", "hua_ji": "wen_qu"},
    "庚": {"hua_lu": "tai_yang", "hua_quan": "wu_qu", "hua_ke": "tai_yin", "hua_ji": "tian_tong"},
    "辛": {"hua_lu": "ju_men", "hua_quan": "tai_yang", "hua_ke": "wen_qu", "hua_ji": "wen_chang"},
    "壬": {"hua_lu": "tian_liang", "hua_quan": "zi_wei", "hua_ke": "zuo_fu", "hua_ji": "wu_qu"},
    "癸": {"hua_lu": "po_jun", "hua_quan": "ju_men", "hua_ke": "tai_yin", "hua_ji": "tan_lang"}
}

class Star:
    def __init__(self, name_key, transformation=None, brightness=None):
        self.key = name_key
        self.name = STAR_MAP.get(name_key, name_key)
        self.transformation = transformation # hua_lu, hua_quan, etc.
        self.brightness = brightness # level_1 to level_5 or M/W/D...

    def __repr__(self):
        t = f"({self.transformation})" if self.transformation else ""
        return f"{self.name}{t}"

class Palace:
    def __init__(self, index, name_key, stem="", branch=""):
        self.index = index
        self.key = name_key # life, spouse etc
        self.name = PALACE_NAMES.get(name_key, name_key)
        self.stem = stem
        self.branch = branch
        self.stars = []

    def add_star(self, star):
        self.stars.append(star)

    def has_star(self, star_key):
        return any(s.key == star_key for s in self.stars)
    
    def not_has_star(self, star_key):
        return not self.has_star(star_key)

    def has_transformation(self, trans_key):
        return any(s.transformation == trans_key for s in self.stars)

    def get_star(self, star_key):
        for s in self.stars:
            if s.key == star_key:
                return s
        return None
    
    def __repr__(self):
        return f"[{self.index}]{self.name}:{self.stars}"

class Chart:
    def __init__(self, palaces, gender="M"):
        self.palaces = palaces # List of 12 Palace objects (ordered 0-11 by index usually, or just a list)
        self.palace_map = {p.key: p for p in palaces} # Helper to get by name
        self.palace_by_idx = {p.index: p for p in palaces}
        self.gender = gender

    def get_palace(self, name_key):
        return self.palace_map.get(name_key)

    def get_palace_by_index(self, index):
        return self.palace_by_idx.get(index % 12)

    def get_relative_palace(self, base_palace_key, offset):
        base = self.get_palace(base_palace_key)
        if not base: return None
        target_idx = (base.index + offset) % 12
        return self.get_palace_by_index(target_idx)

    def get_opposite_palace(self, base_palace_key):
        """對宮 (沖): 本宮 + 6"""
        return self.get_relative_palace(base_palace_key, 6)

    def get_triangular_palaces(self, base_palace_key):
        """三方: 本宮 + 官祿(+4) + 財帛(+8)"""
        p = self.get_palace(base_palace_key)
        if not p: return []
        return [
            p,
            self.get_relative_palace(base_palace_key, 4),
            self.get_relative_palace(base_palace_key, 8)
        ]

    def get_clamp_palaces(self, base_palace_key):
        """夾宮: 前後一宮"""
        return [
            self.get_relative_palace(base_palace_key, -1),
            self.get_relative_palace(base_palace_key, 1)
        ]

# --- Helper: Create Chart from Frontend JSON ---

# Reverse Mappings
REVERSE_PALACE_NAMES = {v: k for k, v in PALACE_NAMES.items()}
REVERSE_STAR_MAP = {v: k for k, v in STAR_MAP.items()}
REVERSE_TRANS_MAP = {v: k for k, v in TRANSFORMATION_MAP.items()}

# Common aliases in frontend data
REVERSE_PALACE_NAMES["交友宮"] = "friends"
REVERSE_PALACE_NAMES["奴僕宮"] = "friends"

REVERSE_STAR_MAP = {v: k for k, v in STAR_MAP.items()}
REVERSE_STAR_MAP["羊刃"] = "qing_yang"
REVERSE_STAR_MAP["陀羅"] = "tuo_luo"
REVERSE_STAR_MAP["鈴星"] = "ling_xing"
REVERSE_STAR_MAP["火星"] = "huo_xing"
REVERSE_STAR_MAP["祿存"] = "lu_cun"
REVERSE_STAR_MAP["文昌"] = "wen_chang"
REVERSE_STAR_MAP["文曲"] = "wen_qu"
REVERSE_STAR_MAP["左輔"] = "zuo_fu"
REVERSE_STAR_MAP["右弼"] = "you_bi"
REVERSE_STAR_MAP["天魁"] = "tian_kui"
REVERSE_STAR_MAP["天鉞"] = "tian_yue"

def create_chart_from_dict(data, gender="M"):
    """
    Creates a Chart object from the frontend chartData JSON structure.
    """
    palaces_list = []
    palaces_by_idx = {}
    
    # Pre-fill with empty palaces to ensure order
    for i in range(12):
        palaces_by_idx[i] = Palace(i, "unknown")

    for item in data:
        idx = item.get("id")
        if idx is None or idx == -1: continue
        
        p_name_zh = item.get("palaceName", "")
        stars_list = item.get("stars", [])
        gan = item.get("gan", "")
        zhi = item.get("zhi", "")
        
        # Determine the logical palace key
        key = "unknown"
        for zh, k in REVERSE_PALACE_NAMES.items():
            if zh in p_name_zh:
                key = k
                break
        
        palace = Palace(idx, key, stem=gan, branch=zhi)
        
        for s in stars_list:
            s_name = s.get("name", "")
            # Clean name (e.g. "紫微 (廟)" -> "紫微")
            clean_name = s_name.split(' ')[0].split('(')[0]
            star_key = REVERSE_STAR_MAP.get(clean_name)
            
            if star_key:
                s_trans = s.get("transformation") or s.get("trans")
                trans_key = REVERSE_TRANS_MAP.get(s_trans) if s_trans else None
                palace.add_star(Star(star_key, transformation=trans_key))
            
            # Special Sihua check if sent as name
            if s_name in ["化祿", "化權", "化科", "化忌"]:
                t_key = REVERSE_TRANS_MAP.get(s_name)
                if t_key:
                    # Look if any existing star should have this trans
                    pass # Handled by data usually, but we keep the independent star for legacy rules

        palaces_by_idx[idx] = palace
    
    palaces_list = [palaces_by_idx[i] for i in range(12)]
    print(f"命盤解析完成，性別: {gender}，解析得 {len([p for p in palaces_list if p.key != 'unknown'])} 個有效宮位。")
    return Chart(palaces_list, gender=gender)

def loose_has_transformation(self, trans_key):
    if any(s.transformation == trans_key for s in self.stars): return True
    if any(s.key == trans_key for s in self.stars): return True
    return False

Palace.has_transformation = loose_has_transformation

# --- Rule Engine ---

def check_condition(chart, condition, context=None):
    if context is None: context = {}
    
    # Base logic operator
    if "logic" in condition:
        logic = condition["logic"]
        sub_criteria = condition["criteria"]
        # Pass context to recursive calls
        # Note: logic AND/OR short-circuiting might affect what details are captured.
        # We need to collect details only for TRUE branches ideally, but collecting all candidates is okay for now
        # OR better: pass new sub-contexts? No, single context is ensuring global capture.
        
        results = [check_condition(chart, c, context) for c in sub_criteria]
        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        elif logic == "NOT":
            return not results[0]
        return False

    # Leaf criteria
    target_str = condition.get("target")
    
    # Handle 'context' targets (gender, etc)
    if target_str == "context":
        if "gender" in condition:
            return chart.gender == condition["gender"]
        return True


    # Resolve target palaces
    targets = []
    
    # Simple predefined names or dynamic resolutions
    if target_str in PALACE_NAMES:
        targets.append(chart.get_palace(target_str))
    
    # Special suffixes for relative positions based on explicit target names usually in parent scope?
    # In this schema, 'target' is often 'life' or 'life_triangle'.
    elif target_str and target_str.endswith("_triangle"):
        base = target_str.replace("_triangle", "")
        targets.extend(chart.get_triangular_palaces(base))
    
    elif target_str and target_str.endswith("_clamp"):
        base = target_str.replace("_clamp", "")
        targets.extend(chart.get_clamp_palaces(base))

    elif target_str and target_str.endswith("_opposite"):
        base = target_str.replace("_opposite", "")
        p = chart.get_opposite_palace(base)
        if p: targets.append(p)

    elif target_str and target_str.startswith("palace_"):
        # e.g. palace_zi -> index 0
        zhi_map = {'zi': 0, 'chou': 1, 'yin': 2, 'mao': 3, 'chen': 4, 'si': 5, 
                   'wu': 6, 'wei': 7, 'shen': 8, 'you': 9, 'xu': 10, 'hai': 11}
        suffix = target_str.replace("palace_", "")
        idx = zhi_map.get(suffix)
        if idx is not None:
            targets.append(chart.get_palace_by_index(idx))

    # Star specific checks on a star object within a palace
    # This requires 'target' to specify a star, e.g. 'spouse_star' + 'star': 'lian_zhen'
    elif target_str and target_str.endswith("_star"):
        base_palace = target_str.replace("_star", "")
        palace = chart.get_palace(base_palace)
        star_key = condition.get("star")
        if palace:
            star = palace.get_star(star_key)
            if not star: return False
            # Check properties of this star
            if "has_trans" in condition:
                return star.transformation in condition["has_trans"]
            if "brightness" in condition:
                # Todo: Implement brightness check
                pass
        return False # If palace not found or star not found

    # Ensure we valid targets
    targets = [t for t in targets if t is not None]

    # Evaluate criteria
    # A rule target can resolve to multiple palaces (e.g., triangle).
    # Leaf conditions should return True if AT LEAST ONE of the target palaces satisfies them.
    for palace in targets:
        match_this_palace = True
        
        # 1. has_branch
        if "has_branch" in condition:
            if palace.index not in condition["has_branch"]: match_this_palace = False
            
        # 2. has_stem
        if match_this_palace and "has_stem" in condition:
            if palace.stem != condition["has_stem"]: match_this_palace = False
            
        # 3. has_star_matching
        if match_this_palace and "has_star_matching" in condition:
             criteria = condition["has_star_matching"]
             found_s = False
             for star in palace.stars:
                 s_m = True
                 if "key" in criteria and star.key != criteria["key"]: s_m = False
                 if s_m and "trans" in criteria and star.transformation != criteria["trans"]: s_m = False
                 if s_m and "self_trans" in criteria:
                      req_t = criteria["self_trans"]
                      if palace.stem in SI_HUA_TABLE and SI_HUA_TABLE[palace.stem].get(req_t) != star.key: s_m = False
                      elif palace.stem not in SI_HUA_TABLE: s_m = False
                 if s_m: found_s = True; break
             if not found_s: match_this_palace = False

        # 4. has_star
        if match_this_palace and "has_star" in condition:
            stars = condition["has_star"]
            stars_list = stars if isinstance(stars, list) else [stars]
            if not any(palace.has_star(s) for s in stars_list): match_this_palace = False

        # 5. not_has_star
        if match_this_palace and "not_has_star" in condition:
            stars = condition["not_has_star"]
            stars_list = stars if isinstance(stars, list) else [stars]
            if any(palace.has_star(s) for s in stars_list): match_this_palace = False

        # 6. has_trans
        if match_this_palace and "has_trans" in condition:
            trans = condition["has_trans"]
            trans_list = trans if isinstance(trans, list) else [trans]
            if not any(palace.has_transformation(t) for t in trans_list): match_this_palace = False

        # 7. self_trans
        if match_this_palace and "self_trans" in condition:
            req_t = condition["self_trans"]
            if palace.stem in SI_HUA_TABLE:
                s_key = SI_HUA_TABLE[palace.stem].get(req_t)
                if not s_key or not palace.has_star(s_key): match_this_palace = False
            else: match_this_palace = False

        # 8. flying_from
        if match_this_palace and "flying_from" in condition and "trans" in condition:
            source_p = chart.get_palace(condition["flying_from"])
            if source_p and source_p.stem in SI_HUA_TABLE:
                s_key = SI_HUA_TABLE[source_p.stem].get(condition["trans"])
                if not s_key or not palace.has_star(s_key): match_this_palace = False
                elif context is not None:
                    star_cn = STAR_MAP.get(s_key, s_key)
                    context["details"].append(f"(飛入: {palace.name}之{star_cn})")
            else: match_this_palace = False

        # 9. Complex Logics
        if match_this_palace and condition.get("no_lucky_stars"):
             lucky = ["zuo_fu", "you_bi", "tian_kui", "tian_yue", "wen_chang", "wen_qu", "lu_cun", "tian_ma"]
             if any(palace.has_star(s) for s in lucky): match_this_palace = False

        if match_this_palace and condition.get("no_main_stars"):
             main = ["zi_wei", "tian_ji", "tai_yang", "wu_qu", "tian_tong", "lian_zhen", "tian_fu", "tai_yin", 
                     "tan_lang", "ju_men", "tian_xiang", "tian_liang", "qi_sha", "po_jun"]
             if any(palace.has_star(s) for s in main): match_this_palace = False

        if match_this_palace:
            # If we reach here, this palace matches the condition.
            if context is not None and "details" in context:
                context["details"].append(f"<{palace.name}>")
            return True # Found AT LEAST ONE match
            
    return False # None of the targets matched

def evaluate_rules(chart, rules):
    results = []
    for rule in rules:
        try:
            context = {"details": []}
            if check_condition(chart, rule["conditions"], context):
                res_obj = rule["result"].copy()
                res_obj["category"] = rule.get("category", "")
                res_obj["description"] = rule.get("description", "")
                
                # --- 新增：識別規則類別類型 ---
                conds = rule["conditions"]
                if "flying_from" in conds:
                    if conds["flying_from"] == "life":
                        res_obj["rule_group"] = "B" # 命宮飛化
                    else:
                        res_obj["rule_group"] = "C" # 宮位間交互飛化
                else:
                    res_obj["rule_group"] = "A" # 星曜坐守與神煞
                
                if context["details"]:
                    unique_details = list(set(context["details"]))
                    
                    # 1. 提取所有標註過的宮位名稱
                    detected_palaces = []
                    for det in unique_details:
                        # 處理 <宮位名稱> 標記
                        m1 = re.search(r"<(.*?)>", det)
                        if m1: detected_palaces.append(m1.group(1))
                        # 處理 (飛入: 宮位之...) 標記
                        m2 = re.search(r"\(飛入: (.*?)之", det)
                        if m2: detected_palaces.append(m2.group(1))
                    
                    if detected_palaces:
                        p_set = []
                        for p in detected_palaces:
                            if p not in p_set: p_set.append(p)
                        target_str = "與".join(p_set)
                        res_obj["detected_palace_names"] = target_str
                        
                        # 2. 自動替換內容中的占位符
                        for field in ["text", "description"]:
                            res_obj[field] = res_obj[field].replace("某宮", target_str)
                            res_obj[field] = res_obj[field].replace("該宮位", target_str)
                            res_obj[field] = res_obj[field].replace("那個宮位", target_str)
                            res_obj[field] = res_obj[field].replace("此宮", target_str)

                results.append(res_obj)
        except Exception as e:
            pass
    return results

# --- Main Test Block ---

if __name__ == "__main__":
    # Mock Data
    p_life = Palace(0, "life")
    p_life.add_star(Star("di_kong"))
    p_life.add_star(Star("lian_zhen", transformation="hua_ji"))
    
    p_spouse = Palace(2, "spouse")
    p_spouse.add_star(Star("lian_zhen", transformation="hua_ji"))

    p_wealth = Palace(4, "wealth")
    p_wealth.add_star(Star("tan_lang"))
    p_wealth.add_star(Star("huo_xing"))

    mock_palaces = [p_life, Palace(1, "siblings"), p_spouse, Palace(3, "kids"), 
                   p_wealth, Palace(5, "health"), Palace(6, "travel"), Palace(7, "friends"),
                   Palace(8, "career"), Palace(9, "property"), Palace(10, "fortune"), Palace(11, "parents")]
    
    mock_chart = Chart(mock_palaces, gender="F") # Female

    # Load Rules
    try:
        with open("ziwei_rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
    except FileNotFoundError:
        print("Rules file not found.")
        rules = []

    # Evaluate
    matched = evaluate_rules(mock_chart, rules)
    print("--- Matched Results ---")
    for res in matched:
        print(f"[{', '.join(res.get('tags', []))}] {res['text']}")
