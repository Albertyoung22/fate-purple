
import json

RULE_FILE = "ziwei_rules.json"

def add_new_rules_v3():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        existing_rules = json.load(f)
    
    # Helper to avoid duplicates
    existing_ids = set(r["id"] for r in existing_rules)
    new_rules_list = []

    def add_rule(rid, cat, desc, cond, res_text, tags=[]):
        if rid in existing_ids: return
        new_rules_list.append({
            "id": rid,
            "category": cat,
            "description": desc,
            "conditions": cond,
            "result": { "text": res_text, "tags": tags }
        })

    # --- Lucky Series ---
    
    # Lucky-01: Life Has ZuoFu OR YouBi
    add_rule("Lucky-01", "life", "有左輔或右弼。", 
        { "logic": "OR", "criteria": [ {"target": "life", "has_star": "zuo_fu"}, {"target": "life", "has_star": "you_bi"} ] },
        "肚量大，氣量很好。", ["personality"])

    # Lucky-02: Life Has ZuoFu
    add_rule("Lucky-02", "life", "有左輔。", 
        { "target": "life", "has_star": "zuo_fu" },
        "講話溫和。", ["personality"])

    # Lucky-03: Life Has YouBi
    add_rule("Lucky-03", "life", "有右弼。", 
        { "target": "life", "has_star": "you_bi" },
        "講話直接，帶點命令式口氣。", ["personality"])

    # Lucky-04: Travel Has ZuoFu/YouBi (Sit/Arch/Clamp)
    # Simplified to Sit or Arch (Triangles) or Clamp. The system doesn't have a single "Clamp/Arch/Sit" operator.
    # We check: Travel(Has), Travel_Triangle(Has), Travel_Clamp(Has).
    # Since Has(List) in Triangle works as "Any in triangle has", we use that.
    star_targets = ["zuo_fu", "you_bi"]
    lucky_04_cond = {
        "logic": "OR",
        "criteria": [
            { "target": "travel", "has_star": star_targets }, # Sit
            { "target": "travel_triangle", "has_star": star_targets }, # Arch
            { "target": "travel_clamp", "has_star": star_targets } # Clamp
        ]
    }
    add_rule("Lucky-04", "travel", "有左輔、右弼(夾/拱/坐)。", lucky_04_cond, "出外運好，即便是不熟的人也會幫忙。", ["travel"])

    # Lucky-05: Spouse Left/Right SINGLE (Sit/Clamp/Arch/Clash) -> Third Party
    # Logic: (Start count of ZF/YB in related palaces) == 1? Hard to express in current JSON logic.
    # Approximation: Has Any(ZF/YB) AND NOT (Has ZF AND Has YB).
    # Sit/Clamp/Arch/Clash = All related.
    # We will approximate to "Spouse or Triangle or Clamp has ZF or YB" AND "NOT (Spouse has ZF & YB)".
    # The rule says "Single". Usually means "Only Left" or "Only Right".
    # Implementation: Spouse Has ZF AND NOT YB -> Bad. Spouse Has YB AND NOT ZF -> Bad.
    lucky_05_cond = {
        "logic": "OR",
        "criteria": [
             { "logic": "AND", "criteria": [ {"target": "spouse", "has_star": "zuo_fu"}, {"target": "spouse", "not_has_star": "you_bi"} ] },
             { "logic": "AND", "criteria": [ {"target": "spouse", "has_star": "you_bi"}, {"target": "spouse", "not_has_star": "zuo_fu"} ] }
        ]
    }
    add_rule("Lucky-05", "spouse", "左輔或右弼單顆出現(坐)。", lucky_05_cond, "易有第三者介入。(需兩顆同宮才算有情有義)。", ["marriage"])

    # Lucky-06: Siblings/Kids/Wealth Has ZF/YB (Sit/Arch...)
    # We do Sit for simplicity as "Arch" for multiple palaces explodes complexity.
    lucky_06_cond = {
        "logic": "OR",
        "criteria": [
            { "target": "siblings", "has_star": ["zuo_fu", "you_bi"] },
            { "target": "kids", "has_star": ["zuo_fu", "you_bi"] },
            { "target": "wealth", "has_star": ["zuo_fu", "you_bi"] }
        ]
    }
    add_rule("Lucky-06", "generic", "兄/子/財 有左輔、右弼。", lucky_06_cond, "兄弟感情好，或容易得到利益。")

    # Lucky-07: Property Has ZF/YB
    add_rule("Lucky-07", "property", "有左輔、右弼。", 
        { "logic": "OR", "criteria": [{"target": "property", "has_star": "zuo_fu"}, {"target": "property", "has_star": "you_bi"}] },
        "是好父母，且有祖產。", ["property"])

    # Lucky-08: Fortune Has ZF + YB (Both)
    add_rule("Lucky-08", "fortune", "有左輔、右弼同宮。",
        { "logic": "AND", "criteria": [{"target": "fortune", "has_star": "zuo_fu"}, {"target": "fortune", "has_star": "you_bi"}] },
        "肚量大，心腸好。", ["personality"])

    # Lucky-09: Parents Has ZF + YB
    add_rule("Lucky-09", "parents", "有左輔、右弼同宮。",
        { "logic": "AND", "criteria": [{"target": "parents", "has_star": "zuo_fu"}, {"target": "parents", "has_star": "you_bi"}] },
        "與父母有緣份。", ["parents"])

    # Lucky-10: Life - Zuo Gui Xiang Gui (Kui/Yue)
    # Sit: Life has Both? Or Life has One, Opposite has One? 
    # Usually "Sit Gui Xiang Gui" = Kui in Life, Yue in Travel (or vice versa).
    # "Have Kui/Yue OR Clamp OR Arch".
    lucky_10_cond = {
        "logic": "OR",
        "criteria": [
            { "target": "life", "has_star": ["tian_kui", "tian_yue"] },
            { "target": "life_triangle", "has_star": ["tian_kui", "tian_yue"] },
            { "target": "life_clamp", "has_star": ["tian_kui", "tian_yue"] }
        ]
    }
    add_rule("Lucky-10", "life", "命宮有天魁天鉞，或夾命/拱命。", lucky_10_cond, "「坐貴向貴」格，一生貴人多。", ["lucky"])

    # Lucky-11: Spouse Has Kui OR Yue
    add_rule("Lucky-11", "spouse", "有天魁或天鉞。",
        { "target": "spouse", "has_star": ["tian_kui", "tian_yue"] },
        "易有第三者。(魁鉞不喜入夫妻宮)。", ["marriage"])

    # Lucky-12: Spouse Has (Kui+Yue) AND Low Sha
    # Low Sha Logic: Not easily implementable "Count < 3".
    # We will implement "Has Kui AND Has Yue".
    add_rule("Lucky-12", "spouse", "有雙貴(魁+鉞)。",
        { "logic": "AND", "criteria": [{"target": "spouse", "has_star": "tian_kui"}, {"target": "spouse", "has_star": "tian_yue"}] },
        "夫妻有情有義。", ["marriage"])

    # Lucky-13: Wealth/Travel/Career/Property/Fortune/Parents Has Kui/Yue
    palace_set = ["wealth", "travel", "career", "property", "fortune", "parents"]
    crit_13 = []
    for p in palace_set:
        crit_13.append({ "target": p, "has_star": ["tian_kui", "tian_yue"] })
    add_rule("Lucky-13", "generic", "財/遷/官/田/福/父 有天魁天鉞。", { "logic": "OR", "criteria": crit_13 }, "皆為吉象。", ["lucky"])

    # Lucky-14: Life Chang/Qu Sit/Arch/Clash
    # Clash is Target+6. Rule engine doesn't have "Clash" explicit but has Triangle (Arch).
    # We approximate with Sit/Triangle.
    add_rule("Lucky-14", "life", "文昌文曲同度、拱照。",
        { "logic": "OR", "criteria": [ {"target": "life", "has_star": ["wen_chang", "wen_qu"]}, {"target": "life_triangle", "has_star": ["wen_chang", "wen_qu"]} ] },
        "正俏(聰明)。", ["personality"])

    # Lucky-15: Life Only Chang OR Only Qu (Single)
    add_rule("Lucky-15", "life", "只有文昌或文曲一顆。",
        { "logic": "OR", "criteria": [ 
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "wen_chang"}, {"target": "life", "not_has_star": "wen_qu"}] },
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "wen_qu"}, {"target": "life", "not_has_star": "wen_chang"}] }
        ]},
        "只是小聰明。", ["personality"])

    # Lucky-16: Life (Chang OR Qu check matched Hua Ji) + YinSha
    add_rule("Lucky-16", "life", "昌曲之一化忌，加陰煞。",
        { "logic": "AND", "criteria": [
            { "logic": "OR", "criteria": [
                {"target": "life", "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
                {"target": "life", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}
            ]},
            { "target": "life", "has_star": "yin_sha" }
        ]},
        "奸詐，會害人。", ["personality"])

    # Lucky-17: Life (Chang/Qu Ji) + TianYao + TianFu
    add_rule("Lucky-17", "life", "昌曲之一化忌，加天姚和天府。",
        { "logic": "AND", "criteria": [
            { "logic": "OR", "criteria": [
                {"target": "life", "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
                {"target": "life", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}
            ]},
            { "target": "life", "has_star": "tian_yao" },
            { "target": "life", "has_star": "tian_fu" }
        ]},
        "會有害人之心。", ["personality"])

    # Lucky-18: Life Chang+Qu+Ke+LongChi+FengGe
    # "Ke" likely means Chang OR Qu has Ke.
    add_rule("Lucky-18", "life", "昌曲+化科+龍池+鳳閣。",
        { "logic": "AND", "criteria": [
            { "target": "life", "has_star": "wen_chang" },
            { "target": "life", "has_star": "wen_qu" },
            { "target": "life", "has_trans": "hua_ke" },
            { "target": "life", "has_star": "long_chi" },
            { "target": "life", "has_star": "feng_ge" }
        ]},
        "非常聰明，第六感非常準。", ["personality"])

    # Lucky-19: Life WenChang + Si(5)
    add_rule("Lucky-19", "life", "文昌在巳宮。",
        { "logic": "AND", "criteria": [ {"target": "life", "has_star": "wen_chang"}, {"target": "life", "has_branch": [5]} ]},
        "考運特別好。", ["academic"])

    # Lucky-20: Male, Fortune, Chang+Qu
    add_rule("Lucky-20", "fortune", "文昌文曲同宮 (男命)。",
        { "logic": "AND", "criteria": [ {"target": "context", "gender": "M"}, {"target": "fortune", "has_star": "wen_chang"}, {"target": "fortune", "has_star": "wen_qu"} ]},
        "「玉袖天香格」，風流。", ["personality"])

    # Lucky-21: Female, Fortune, Chang+Qu (Sit or Arch)
    add_rule("Lucky-21", "fortune", "文昌文曲同宮或拱照 (女命)。",
        { "logic": "AND", "criteria": [ 
            {"target": "context", "gender": "F"}, 
            { "logic": "OR", "criteria": [
                { "logic": "AND", "criteria": [{"target": "fortune", "has_star": "wen_chang"}, {"target": "fortune", "has_star": "wen_qu"}] },
                { "logic": "AND", "criteria": [{"target": "fortune_triangle", "has_star": "wen_chang"}, {"target": "fortune_triangle", "has_star": "wen_qu"}] }
            ]}
        ]},
        "風流 (拱照比同宮更風流)。", ["personality"])

    # Lucky-22: Chart (Generic). Chang/Qu Ji + TianXing
    # We iterate all palaces for "Any Palace has..."
    crit_22 = []
    for p in palaces:
        crit_22.append({
            "logic": "AND",
            "criteria": [
                { "logic": "OR", "criteria": [
                    {"target": p, "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
                    {"target": p, "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}
                ]},
                { "target": p, "has_star": "tian_xing" }
            ]
        })
    add_rule("Lucky-22", "generic", "昌曲化忌加天刑。", { "logic": "OR", "criteria": crit_22 }, "不要跟他吵架，他錯的也會講成對的。", ["personality"])

    # Lucky-23: Kids, Chang/Qu Ji
    add_rule("Lucky-23", "kids", "文昌或文曲化忌。",
        { "logic": "OR", "criteria": [
            {"target": "kids", "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
            {"target": "kids", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}
        ]},
        "小孩會說謊。", ["kids"])

    # Lucky-24: Property/Career Chang/Qu Ji
    add_rule("Lucky-24", "generic", "田/官 文昌或文曲化忌。",
        { "logic": "OR", "criteria": [
            {"target": "property", "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
            {"target": "property", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}},
            {"target": "career", "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}},
            {"target": "career", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}
        ]},
        "文書產權合約要看清楚，否則易吃虧。", ["career", "property"])

    # Lucky-25: Life LongChi/FengGe
    add_rule("Lucky-25", "life", "有龍池、鳳閣。",
        { "logic": "OR", "criteria": [ {"target": "life", "has_star": "long_chi"}, {"target": "life", "has_star": "feng_ge"} ]},
        "肚量大，氣度恢弘，機遇較好。", ["personality"])

    # Lucky-26: Life LuCun
    add_rule("Lucky-26", "life", "有祿存。", { "target": "life", "has_star": "lu_cun" }, "正財好，幽默。", ["wealth"])

    # Lucky-27: Life LongChi + FengGe
    add_rule("Lucky-27", "life", "龍池鳳閣同坐。",
        { "logic": "AND", "criteria": [ {"target": "life", "has_star": "long_chi"}, {"target": "life", "has_star": "feng_ge"} ]},
        "一生有較好的機運。", ["luck"])

    # Lucky-28: Spouse LongChi + FengGe
    add_rule("Lucky-28", "spouse", "龍池鳳閣同坐。",
        { "logic": "AND", "criteria": [ {"target": "spouse", "has_star": "long_chi"}, {"target": "spouse", "has_star": "feng_ge"} ]},
        "易嫁好丈夫娶美妻，感情好不易離婚。", ["marriage"])

    # Lucky-29: Spouse LongChi + FengGe + Double Lu (HuaLu + LuCun)
    add_rule("Lucky-29", "spouse", "龍池鳳閣加雙祿。",
        { "logic": "AND", "criteria": [ 
            {"target": "spouse", "has_star": "long_chi"}, 
            {"target": "spouse", "has_star": "feng_ge"},
            {"target": "spouse", "has_star": "lu_cun"},
            {"target": "spouse", "has_trans": "hua_lu"}
        ]},
        "即使本人條件差，也能嫁娶到帥/美又有錢的配偶。", ["marriage"])

    # Lucky-30: Career LongChi + FengGe
    add_rule("Lucky-30", "career", "龍池鳳閣同度。",
        { "logic": "AND", "criteria": [ {"target": "career", "has_star": "long_chi"}, {"target": "career", "has_star": "feng_ge"} ]},
        "工作上有好的機遇。", ["career"])

    # --- Sha Series ---

    # Sha-01: Huo/Ling Clamp or Arch
    # Clamp Life or Arch Life.
    sha_01_cond = {
        "logic": "OR",
        "criteria": [
            { "target": "life_triangle", "has_star": ["huo_xing", "ling_xing"] },
            { "target": "life_clamp", "has_star": ["huo_xing", "ling_xing"] }
        ]
    }
    add_rule("Sha-01", "life", "火星、鈴星夾命或拱命。", sha_01_cond, "情緒不定，莫名其妙發脾氣。", ["personality"])

    # Sha-02: Fire/Bell + Greed (Huo/Ling Tan) + LuCun/TianMa Arch
    # Check Life Has (Tan + Huo) OR (Tan + Ling). AND Life_Triangle Has (LuCun OR TianMa).
    sha_02_cond = {
        "logic": "AND",
        "criteria": [
            { "logic": "OR", "criteria": [
                { "logic": "AND", "criteria": [ {"target": "life", "has_star": "tan_lang"}, {"target": "life", "has_star": "huo_xing"} ] },
                { "logic": "AND", "criteria": [ {"target": "life", "has_star": "tan_lang"}, {"target": "life", "has_star": "ling_xing"} ] }
            ]},
            { "target": "life_triangle", "has_star": ["lu_cun", "tian_ma"] }
        ]
    }
    add_rule("Sha-02", "life", "火貪或鈴貪格，有祿存或天馬拱照。", sha_02_cond, "易有偏財，中大獎機會。", ["wealth"])

    # Sha-03: Travel Huo/Ling Clamp/Arch AND (HuaQuan + QingYang)
    sha_03_cond = {
        "logic": "AND",
        "criteria": [
            { "logic": "OR", "criteria": [
                { "target": "travel_triangle", "has_star": ["huo_xing", "ling_xing"] },
                { "target": "travel_clamp", "has_star": ["huo_xing", "ling_xing"] }
            ]},
            { "target": "travel", "has_trans": "hua_quan" },
            { "target": "travel", "has_star": "qing_yang" }
        ]
    }
    add_rule("Sha-03", "travel", "火鈴夾或拱，且有化權、羊刃。", sha_03_cond, "易出意外、車關。", ["health"])

    # Sha-04: Si(5) or Hai(11) Has DiKong + DiJie
    sha_04_cond = {
        "logic": "AND",
        "criteria": [
            { "logic": "OR", "criteria": [ {"target": "palace_si", "has_star": "di_kong"}, {"target": "palace_hai", "has_star": "di_kong"} ] }, # Placeholder target needed?
            # Actually logic: (Si Has Kong AND Si Has Jie) OR (Hai Has Kong AND Hai Has Jie)
            { "logic": "OR", "criteria": [
                { "logic": "AND", "criteria": [{"target": "palace_si", "has_star": "di_kong"}, {"target": "palace_si", "has_star": "di_jie"}] },
                { "logic": "AND", "criteria": [{"target": "palace_hai", "has_star": "di_kong"}, {"target": "palace_hai", "has_star": "di_jie"}] }
            ]}
        ]
    }
    # palace_si/hai resolution is usually implied by index logic or helper.
    # In rule_engine: palace_zi -> 0. si -> 5. hai -> 11.
    add_rule("Sha-04", "generic", "巳/亥 有地空、地劫。", sha_04_cond, "有爛桃花。", ["marriage"])

    # Sha-05: Life Kong/Jie Sit/Clamp/Arch/Clash
    add_rule("Sha-05", "life", "空劫夾、拱、坐。", 
        { "logic": "OR", "criteria": [
            {"target": "life", "has_star": ["di_kong", "di_jie"]},
            {"target": "life_triangle", "has_star": ["di_kong", "di_jie"]},
            {"target": "life_clamp", "has_star": ["di_kong", "di_jie"]}
        ]},
        "最好有一技之長，否則人生渺茫。", ["career"])

    # Sha-06: 6 Relatives Has Kong/Jie
    relatives = ["parents", "siblings", "spouse", "kids", "friends", "health"]
    crit_06 = []
    for p in relatives:
        crit_06.append({ "target": p, "has_star": ["di_kong", "di_jie"] })
    add_rule("Sha-06", "generic", "六親宮 有地空、地劫。", { "logic": "OR", "criteria": crit_06 }, "相聚時間少，聚少離多較好。", ["marriage"])

    # Sha-07: Wealth/Prop/Fortune Has Kong/Jie
    crit_07 = []
    for p in ["wealth", "property", "fortune"]:
        crit_07.append({ "target": p, "has_star": ["di_kong", "di_jie"] })
    add_rule("Sha-07", "generic", "財/田/福 有地空、地劫。", { "logic": "OR", "criteria": crit_07 }, "財不聚，福氣被空掉。", ["wealth"])

    # Sha-08: Life/Body/Fortune Has Kong/Jie + TianKu
    # Body (Shen) palace not explicitly in static target list usually, but let's try.
    # If not supported, we skip Body.
    # We will use Life and Fortune.
    sha_08_cond = {
        "logic": "OR",
        "criteria": [
            { "logic": "AND", "criteria": [{"target": "life", "has_star": ["di_kong", "di_jie"]}, {"target": "life", "has_star": "tian_ku"}] },
            { "logic": "AND", "criteria": [{"target": "fortune", "has_star": ["di_kong", "di_jie"]}, {"target": "fortune", "has_star": "tian_ku"}] }
        ]
    }
    add_rule("Sha-08", "life", "命/福 空劫加天哭。", sha_08_cond, "思想較負面悲觀。", ["personality"])

    # Sha-09: Life QingYang
    add_rule("Sha-09", "life", "有擎羊。", {"target": "life", "has_star": "qing_yang"}, "講話直、衝、辣。", ["personality"])

    # Sha-10: Any Palace QingYang + WuQu(HuaJi)
    crit_10 = []
    for p in palaces:
        crit_10.append({
            "logic": "AND",
            "criteria": [
                {"target": p, "has_star": "qing_yang"},
                {"target": p, "has_star_matching": {"key": "wu_qu", "trans": "hua_ji"}}
            ]
        })
    add_rule("Sha-10", "generic", "擎羊加武曲化忌。", { "logic": "OR", "criteria": crit_10 }, "因財動刀，因財被劫。", ["wealth"])

    # Sha-11: QingYang + (LianZhen OR JuMen)
    crit_11 = []
    for p in palaces:
        crit_11.append({
            "logic": "AND",
            "criteria": [
                {"target": p, "has_star": "qing_yang"},
                {"target": p, "has_star": ["lian_zhen", "ju_men"]}
            ]
        })
    add_rule("Sha-11", "generic", "擎羊加廉貞或巨門。", { "logic": "OR", "criteria": crit_11 }, "是非多、官司、意外。", ["health"])

    # Sha-12: Travel QingYang
    add_rule("Sha-12", "travel", "有擎羊。", {"target": "travel", "has_star": "qing_yang"}, "意外多見血。", ["health"])

    # Sha-13: Career QingYang
    add_rule("Sha-13", "career", "有擎羊。", {"target": "career", "has_star": "qing_yang"}, "宜做拿刀的職業(醫、屠、廚)。", ["career"])

    # Sha-14: Health QingYang
    add_rule("Sha-14", "health", "有擎羊。", {"target": "health", "has_star": "qing_yang"}, "一生至少開一次刀。", ["health"])

    # Sha-15: Life QingYang + HuaJi
    add_rule("Sha-15", "life", "擎羊加化忌。", 
        {"logic": "AND", "criteria": [{"target": "life", "has_star": "qing_yang"}, {"target": "life", "has_trans": "hua_ji"}]},
        "脾氣壞。", ["personality"])

    # Sha-16: Spouse QingYang + HuaJi
    add_rule("Sha-16", "spouse", "擎羊加化忌。", 
        {"logic": "AND", "criteria": [{"target": "spouse", "has_star": "qing_yang"}, {"target": "spouse", "has_trans": "hua_ji"}]},
        "夫妻像仇人。", ["marriage"])

    # Sha-17: Life TuoLuo
    add_rule("Sha-17", "life", "有陀羅。", {"target": "life", "has_star": "tuo_luo"}, "易輕信剛認識的人，做事拖拉。", ["personality"])

    # Sha-18 to 21: TuoLuo in Spouse/Wealth/Health/Travel
    add_rule("Sha-18", "spouse", "有陀羅。", {"target": "spouse", "has_star": "tuo_luo"}, "結婚拖，離婚也拖。", ["marriage"])
    add_rule("Sha-19", "wealth", "有陀羅。", {"target": "wealth", "has_star": "tuo_luo"}, "賺錢較拖磨。", ["wealth"])
    add_rule("Sha-20", "health", "有陀羅。", {"target": "health", "has_star": "tuo_luo"}, "牙齒不好，易有慢性病。", ["health"])
    add_rule("Sha-21", "travel", "有陀羅。", {"target": "travel", "has_star": "tuo_luo"}, "不利出外，意外屬內傷。", ["health"])
    add_rule("Sha-22", "health", "有陰煞。", {"target": "health", "has_star": "yin_sha"}, "有暗病。", ["health"])

    # Sha-24: HuaJi + TianXing + ShaStar (Any) - wait, already discussed Sha-24. Skipped 23 (Flow).
    sha_stars = ["qing_yang", "tuo_luo", "huo_xing", "ling_xing", "di_kong", "di_jie"]
    crit_24 = []
    for p in palaces:
        crit_24.append({
            "logic": "AND",
            "criteria": [
                {"target": p, "has_trans": "hua_ji"},
                {"target": p, "has_star": "tian_xing"},
                {"target": p, "has_star": sha_stars}
            ]
        })
    add_rule("Sha-24", "generic", "化忌加天刑加煞星。", { "logic": "OR", "criteria": crit_24 }, "在哪個宮位都差。")

    # --- Misc Series ---
    
    # Misc-05: LuCun + TianMa
    crit_05 = []
    for p in palaces:
        crit_05.append({
            "logic": "AND", 
            "criteria": [{"target": p, "has_star": "lu_cun"}, {"target": p, "has_star": "tian_ma"}]
        })
    add_rule("Misc-05", "generic", "祿存加天馬(同宮)。", { "logic": "OR", "criteria": crit_05 }, "祿馬交馳，愈動愈生財。", ["wealth"])

    # Misc-06: HuoXing + TianMa
    crit_06 = []
    for p in palaces:
        crit_06.append({
            "logic": "AND", 
            "criteria": [{"target": p, "has_star": "huo_xing"}, {"target": p, "has_star": "tian_ma"}]
        })
    add_rule("Misc-06", "generic", "火星加天馬(同宮)。", { "logic": "OR", "criteria": crit_06 }, "戰馬，無頭蒼蠅忙不知在忙啥。")

    # Misc-07: HuaJi + TianMa
    crit_07 = []
    for p in palaces:
        crit_07.append({
            "logic": "AND", 
            "criteria": [{"target": p, "has_trans": "hua_ji"}, {"target": p, "has_star": "tian_ma"}]
        })
    add_rule("Misc-07", "generic", "化忌加天馬(同宮)。", { "logic": "OR", "criteria": crit_07 }, "病馬，遭人中傷、有麻煩。")

    # Misc-08: Female Spouse TianMa
    add_rule("Misc-08", "spouse", "有天馬 (女命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "F"}, {"target": "spouse", "has_star": "tian_ma"}] },
        "嫁外國人或外縣市好。", ["marriage"])

    # Misc-09 to 13: Tian姚
    add_rule("Misc-09", "life", "有天姚。", {"target": "life", "has_star": "tian_yao"}, "不易相信人，桃花多防水厄。", ["personality"])
    add_rule("Misc-10", "spouse", "有天姚。", {"target": "spouse", "has_star": "tian_yao"}, "10個有7個配偶會劈腿。", ["marriage"])
    add_rule("Misc-11", "fortune", "有天姚。", {"target": "fortune", "has_star": "tian_yao"}, "常一見鍾情，需性慰藉。", ["personality"])
    add_rule("Misc-12", "life", "天姚在丑未。", { "logic": "AND", "criteria": [{"target": "life", "has_star": "tian_yao"}, {"target": "life", "has_branch": [1, 7]}] }, "騷包。", ["personality"])

    # Misc-13: Life HongLuan (Simple)
    add_rule("Misc-13", "life", "紅鸞。", {"target": "life", "has_star": "hong_luan"}, "有人緣。", ["personality"])

    # Misc-15: Health HongLuan + HuaJi
    add_rule("Misc-15", "health", "紅鸞加化忌。", 
        { "logic": "AND", "criteria": [{"target": "health", "has_star": "hong_luan"}, {"target": "health", "has_trans": "hua_ji"}] },
        "有血光。", ["health"])
    
    # Misc-16: Wealth/Life Has XianChi
    add_rule("Misc-16", "generic", "財/命 有咸池。",
        { "logic": "OR", "criteria": [{"target": "life", "has_star": "xian_chi"}, {"target": "wealth", "has_star": "xian_chi"}] },
        "會亂花錢，沒錢借來開。", ["wealth"])

    # --- Star Series ---

    # Star-01: Life ZiPo / ZiTan / ZiSha
    star_01_cond = {
        "logic": "OR",
        "criteria": [
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "zi_wei"}, {"target": "life", "has_star": "po_jun"}] },
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "zi_wei"}, {"target": "life", "has_star": "tan_lang"}] },
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "zi_wei"}, {"target": "life", "has_star": "qi_sha"}] }
        ]
    }
    add_rule("Star-01", "life", "紫破/紫貪/紫殺。", star_01_cond, "情緒化，抗壓性好。", ["personality"])

    # Star-02: Life Ziwei+TianXiang in Chen(4)/Xu(10)
    star_02_cond = {
        "logic": "AND",
        "criteria": [
            {"target": "life", "has_star": "zi_wei"},
            {"target": "life", "has_star": "tian_xiang"},
            {"target": "life", "has_branch": [4, 10]}
        ]
    }
    add_rule("Star-02", "life", "紫相在辰戌。", star_02_cond, "無情無義，利用人。", ["personality"])

    # Star-03: Life Ziwei + Sha
    add_rule("Star-03", "life", "紫微遇煞多。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "zi_wei"}, {"target": "life", "has_star": sha_stars}]},
        "想當老大，獨斷無理性。", ["personality"])

    # Star-04: Parents Ziwei + Quan
    add_rule("Star-04", "parents", "紫微化權。",
        { "target": "parents", "has_star_matching": {"key": "zi_wei", "trans": "hua_quan"} },
        "父親教小孩很嚴格。", ["parents"])

    # Star-05: Fortune TianJi + HuaJi
    add_rule("Star-05", "fortune", "天機化忌坐福德。",
        { "target": "fortune", "has_star_matching": {"key": "tian_ji", "trans": "hua_ji"} },
        "有自殺傾向，躁鬱、憂鬱。", ["health"])

    # Star-06: Female Life TianJi in Zi(0)/Wu(6)
    add_rule("Star-06", "life", "天機在子午 (女命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "F"}, {"target": "life", "has_star": "tian_ji"}, {"target": "life", "has_branch": [0, 6]}] },
        "有幫夫運。", ["marriage"])

    # Star-07: TaiYang(Zi) + HuaJi + QingYang + TianXing
    add_rule("Star-07", "life", "太陽(子)化忌+羊+刑。",
        { "logic": "AND", "criteria": [
            {"target": "life", "has_branch": [0]},
            {"target": "life", "has_star_matching": {"key": "tai_yang", "trans": "hua_ji"}},
            {"target": "life", "has_star": "qing_yang"},
            {"target": "life", "has_star": "tian_xing"}
        ]},
        "容易情殺談判決裂。", ["marriage"])

    # Star-08: Life TaiYang in Wu(6)
    add_rule("Star-08", "life", "太陽在午。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "tai_yang"}, {"target": "life", "has_branch": [6]}] },
        "大方但存不住錢。", ["wealth"])

    # Star-09: Life WuQu (Male Good / Female Bad) - This rule description says "Li Nan Bu Li Nu, Gu Ke".
    # Implementation: If Female, Result "Lonely".
    add_rule("Star-09", "life", "武曲 (女命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "F"}, {"target": "life", "has_star": "wu_qu"}] },
        "帶孤剋，不利感情。", ["personality"])

    # Star-10: Chart WuQu + HuaJi
    # "Don't play stocks". Generic.
    crit_10s = []
    for p in palaces:
        crit_10s.append({ "target": p, "has_star_matching": {"key": "wu_qu", "trans": "hua_ji"} })
    add_rule("Star-10", "generic", "武曲化忌。", { "logic": "OR", "criteria": crit_10s }, "不可玩股票。", ["wealth"])

    # Star-11: Wealth WuQu + QiSha
    add_rule("Star-11", "wealth", "武曲七殺。",
        { "logic": "AND", "criteria": [{"target": "wealth", "has_star": "wu_qu"}, {"target": "wealth", "has_star": "qi_sha"}] },
        "適合技術性工作。", ["career"])

    # Star-12: Male Life TianTong + TaiYin in Wu(6)
    add_rule("Star-12", "life", "天同太陰在午 (男命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "M"}, {"target": "life", "has_star": "tian_tong"}, {"target": "life", "has_star": "tai_yin"}, {"target": "life", "has_branch": [6]}] },
        "想找有錢女人少奮鬥。", ["marriage"])

    # Star-13: Life TianTong + TuoLuo
    add_rule("Star-13", "life", "天同加陀羅。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "tian_tong"}, {"target": "life", "has_star": "tuo_luo"}] },
        "易胖。", ["appearance"])

    # Star-14: Life LianZhen + TianXiang + Sha + Zi/Wu
    add_rule("Star-14", "life", "廉相在子午遇煞。",
        { "logic": "AND", "criteria": [
            {"target": "life", "has_star": "lian_zhen"}, {"target": "life", "has_star": "tian_xiang"}, 
            {"target": "life", "has_branch": [0, 6]},
            {"target": "life", "has_star": sha_stars}
        ] },
        "有牢獄之災。", ["career"])

    # Star-15: Generic LianZhen(Ji) + TianXing + BaiHu (White Tiger)
    # White Tiger check requires Star map. Assuming 'bai_hu' key exists in future map or frontend. 
    # I will add check.
    crit_15 = []
    for p in palaces:
        crit_15.append({
            "logic": "AND",
            "criteria": [
                {"target": p, "has_star_matching": {"key": "lian_zhen", "trans": "hua_ji"}},
                {"target": p, "has_star": "tian_xing"},
                {"target": p, "has_star": "bai_hu"}
            ]
        })
    add_rule("Star-15", "generic", "廉忌+天刑+白虎。", { "logic": "OR", "criteria": crit_15 }, "官司重災區。", ["legal"])

    # Star-17: Life TianFu + WenQu(Ji)
    add_rule("Star-17", "life", "天府加文曲化忌。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "tian_fu"}, {"target": "life", "has_star_matching": {"key": "wen_qu", "trans": "hua_ji"}}] },
        "記恨一輩子，會報復。", ["personality"])

    # Star-18: Male Life TaiYin
    add_rule("Star-18", "life", "太陰 (男命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "M"}, {"target": "life", "has_star": "tai_yin"}] },
        "動作娘、會煮飯做家事。", ["personality"])

    # Star-19: Spouse TaiYin(Ji) + TianKu
    add_rule("Star-19", "spouse", "太陰化忌加天哭。",
        { "logic": "AND", "criteria": [{"target": "spouse", "has_star_matching": {"key": "tai_yin", "trans": "hua_ji"}}, {"target": "spouse", "has_star": "tian_ku"}] },
        "妻易死亡。", ["marriage"])

    # Star-20: Generic TanLang + TuoLuo
    crit_20 = []
    for p in palaces:
        crit_20.append({"logic": "AND", "criteria": [{"target": p, "has_star": "tan_lang"}, {"target": p, "has_star": "tuo_luo"}]})
    add_rule("Star-20", "generic", "貪狼加陀羅。", { "logic": "OR", "criteria": crit_20 }, "風流彩杖。", ["marriage"])

    # Star-21: Generic HuoTan / LingTan -> Burst Wealth
    # Ideally checking Life or Wealth. Let's do Life+Wealth.
    star_21_targets = ["life", "wealth"]
    star_21_crit = []
    for p in star_21_targets:
        star_21_crit.append({
            "logic": "OR",
            "criteria": [
                { "logic": "AND", "criteria": [{"target": p, "has_star": "tan_lang"}, {"target": p, "has_star": "huo_xing"}] },
                { "logic": "AND", "criteria": [{"target": p, "has_star": "tan_lang"}, {"target": p, "has_star": "ling_xing"}] }
            ]
        })
    add_rule("Star-21", "generic", "火貪、鈴貪。", { "logic": "OR", "criteria": star_21_crit }, "橫發。", ["wealth"])

    # Star-22: Generic TanLang + WenChang(Ji)
    crit_22s = []
    for p in palaces:
        crit_22s.append({"logic": "AND", "criteria": [{"target": p, "has_star": "tan_lang"}, {"target": p, "has_star_matching": {"key": "wen_chang", "trans": "hua_ji"}}]})
    add_rule("Star-22", "generic", "貪狼加文昌化忌。", { "logic": "OR", "criteria": crit_22s }, "易說謊、從高處落下。", ["personality"])

    # Star-23: Generic JuMen(Ji) + TianXing
    crit_23 = []
    for p in palaces:
        crit_23.append({"logic": "AND", "criteria": [{"target": p, "has_star_matching": {"key": "ju_men", "trans": "hua_ji"}}, {"target": p, "has_star": "tian_xing"}]})
    add_rule("Star-23", "generic", "巨門化忌加天刑。", { "logic": "OR", "criteria": crit_23 }, "算命說壞的一定準。", ["personality"])

    # Star-24: JuMen + Yang + Yao (Anywhere)
    crit_24s = []
    for p in palaces:
        crit_24s.append({"logic": "AND", "criteria": [{"target": p, "has_star": "ju_men"}, {"target": p, "has_star": "qing_yang"}, {"target": p, "has_star": "tian_yao"}]})
    add_rule("Star-24", "generic", "巨門+羊+姚。", { "logic": "OR", "criteria": crit_24s }, "性生活不正常。", ["health"])

    # Star-25: Life/Fortune TianXiang + TianYao
    star_25_cond = {
        "logic": "OR",
        "criteria": [
            { "logic": "AND", "criteria": [{"target": "life", "has_star": "tian_xiang"}, {"target": "life", "has_star": "tian_yao"}] },
            { "logic": "AND", "criteria": [{"target": "fortune", "has_star": "tian_xiang"}, {"target": "fortune", "has_star": "tian_yao"}] }
        ]
    }
    add_rule("Star-25", "life", "天相加天姚。", star_25_cond, "不要碰毒品，易早死。", ["health"])

    # Star-26: Female Life TianLiang in Wei(7) + MuYu
    # MuYu 12-stage? If defined as star, ok.
    add_rule("Star-26", "life", "天梁(未)加沐浴 (女命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "F"}, {"target": "life", "has_star": "tian_liang"}, {"target": "life", "has_branch": [7]}, {"target": "life", "has_star": "mu_yu"}] },
        "執著愛一個男生。", ["marriage"])

    # Star-27: Life QiSha "Chong Feng" (Double? Or meeting another QiSha? Impossible physically to have 2 main stars of same name)
    # Maybe "QiSha + QiSha Flow"? Assuming user means just "QiSha in Life". Or "QiSha Repeating" (Destiny + Year).
    # Description "Ten lives nine not firm".
    # I will assume just "QiSha in Life" for now or maybe "QiSha + Yang"?
    # User text: "QiSha Chong Feng". 
    # Usually "Chong Feng" means Meeting again in flow.
    # I will stick to "Life has QiSha" for base chart interpretation? No, that's too common.
    # I'll enable it only for Flow context if I could.
    # I will Use "Life has QiSha" for now, but tag implies severity.
    # Let's add it as "QiSha in Life" but note it's generic.
    add_rule("Star-27", "life", "七殺坐命。", { "target": "life", "has_star": "qi_sha" }, "十生九不牢(兇案/金錢重損)。(需逢煞才驗)", ["personality"])

    # Star-28: Female Fortune QiSha
    add_rule("Star-28", "fortune", "七殺在福德 (女命)。",
        { "logic": "AND", "criteria": [{"target": "context", "gender": "F"}, {"target": "fortune", "has_star": "qi_sha"}] },
        "會拋家棄子。", ["marriage"])

    # Star-29: Life PoJun + WenQu
    add_rule("Star-29", "life", "破軍加文曲。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "po_jun"}, {"target": "life", "has_star": "wen_qu"}] },
        "眾水朝東，好頭沒好尾。", ["personality"])

    # Star-30: Life PoJun in Zi(0)
    add_rule("Star-30", "life", "破軍在子。",
        { "logic": "AND", "criteria": [{"target": "life", "has_star": "po_jun"}, {"target": "life", "has_branch": [0]}] },
        "子女不錯。", ["kids"])

    # Append
    existing_rules.extend(new_rules_list)
    
    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_rules, f, ensure_ascii=False, indent=4)
    print(f"Added {len(new_rules_list)} new Lucky/Sha/Star/Misc rules.")

palaces = ["life", "siblings", "spouse", "kids", "wealth", "health", 
           "travel", "friends", "career", "property", "fortune", "parents"]

if __name__ == "__main__":
    add_new_rules_v3()
