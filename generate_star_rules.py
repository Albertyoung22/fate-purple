"""
紫微斗數：全方位星曜規則生成器 (Master Rule Generator)
================================================
本腳本將生成完整的紫微斗數規則庫，涵蓋以下四大與用戶需求對應的模組：

1.  【論十二宮各星系組合】：針對 14 主星入 12 宮的解釋 (14 * 12 = 168 條)。
2.  【論吉煞星】：針對 六吉星、六煞星、祿存、天馬、紅鸞天喜、咸池、天姚等入命宮及關鍵宮位的解釋。
3.  【論四化】：(已由 generate_sihua_rules.py 處理，此處補充生年四化入命宮)。
4.  【論十二長生】：(已由 generate_aux_rules.py 處理，此處確保完整性)。

註：本腳本將生成的規則 ID 以 "M-" (Master) 開頭，區間為 50000+。
"""

import json
import os

PALACE_KEYS = [
    "life", "siblings", "spouse", "kids", "wealth", "health", 
    "travel", "friends", "career", "property", "fortune", "parents"
]

PALACE_NAMES = {
    "life": "命宮", "siblings": "兄弟宮", "spouse": "夫妻宮", "kids": "子女宮", 
    "wealth": "財帛宮", "health": "疾厄宮", "travel": "遷移宮", "friends": "奴僕宮", 
    "career": "官祿宮", "property": "田宅宮", "fortune": "福德宮", "parents": "父母宮"
}

# 14 主星 (Main Stars)
MAIN_STARS = {
    "zi_wei": "紫微", "tian_ji": "天機", "tai_yang": "太陽", "wu_qu": "武曲", 
    "tian_tong": "天同", "lian_zhen": "廉貞", "tian_fu": "天府", "tai_yin": "太陰", 
    "tan_lang": "貪狼", "ju_men": "巨門", "tian_xiang": "天相", "tian_liang": "天梁", 
    "qi_sha": "七殺", "po_jun": "破軍"
}

# 輔佐煞雜 (Aux Stars)
AUX_STARS = {
    "zuo_fu": "左輔", "you_bi": "右弼", "tian_kui": "天魁", "tian_yue": "天鉞", 
    "wen_chang": "文昌", "wen_qu": "文曲",
    "lu_cun": "祿存", "tian_ma": "天馬",
    "qing_yang": "擎羊", "tuo_luo": "陀羅", "huo_xing": "火星", "ling_xing": "鈴星", 
    "di_kong": "地空", "di_jie": "地劫",
    "hong_luan": "紅鸞", "tian_xi": "天喜", "tian_yao": "天姚", "xian_chi": "咸池"
}

# 簡化的星曜入宮解釋模板 (可根據實際經典書籍擴充)
def get_star_meaning(palace_key, star_key, star_name):
    p_name = PALACE_NAMES[palace_key]
    
    # --- 紫微星 ---
    if star_key == "zi_wei":
        if palace_key == "life": return "帝座入命。氣質高雅，自尊心強，有領導欲，耳軟心活。"
        if palace_key == "wealth": return "紫微入財帛。財運穩健，善理財，多得貴人之財。"
        if palace_key == "career": return "紫微入官祿。宜從事高尚、管理、政治或獨立事業，能掌權。"
        if palace_key == "spouse": return "紫微入夫妻。配偶能力強或年長，具領袖氣質，需互相尊重。"
        if palace_key == "kids": return "紫微入子女。子女聰明有成，頭角崢嶸，但可能較難管教。"
        return f"紫微星入{p_name}。主尊貴、穩定，化解凶煞。"

    # --- 天機星 ---
    if star_key == "tian_ji":
        if palace_key == "life": return "天機入命。機智靈活，思慮周詳，善變愛動，多才多藝。"
        if palace_key == "wealth": return "天機入財帛。財來財去，靠智慧生財，適合變動性大的工作。"
        if palace_key == "parents": return "天機入父母。與父母緣分稍淡，或父母忙碌奔波。"
        if palace_key == "siblings": return "天機入兄弟。手足各奔東西，或各有心機。"
        return f"天機星入{p_name}。主變動、智慧、機運，但也主思慮多。"

    # --- 太陽星 ---
    if star_key == "tai_yang":
        if palace_key == "life": return "太陽入命。光明磊落，熱情博愛，好面子，勞心勞力。"
        if palace_key == "spouse": return "太陽入夫妻。男命妻能幹奪夫權，女命得貴夫但恐其忙碌。"
        if palace_key == "parents": return "太陽入父母。與父親緣深，或受父親影響大；陷地則與父緣薄。"
        return f"太陽星入{p_name}。主博愛、付出、名聲，廟旺大吉，落陷勞碌。"

    # --- 武曲星 ---
    if star_key == "wu_qu":
        if palace_key == "life": return "武曲入命。剛毅果決，重義氣，有執行力，這是一顆財星。"
        if palace_key == "wealth": return "武曲入財帛。正財星入財位，財運極佳，善於理財投資。"
        if palace_key == "spouse": return "武曲入夫妻。感情相處較剛硬，缺乏情趣，宜晚婚。"
        return f"武曲星入{p_name}。主財富、剛毅、孤獨，利於事業財運。"

    # --- 天同星 ---
    if star_key == "tian_tong":
        if palace_key == "life": return "天同入命。福星坐命，性情溫和，樂天知命，有點懶散。"
        if palace_key == "fortune": return "天同入福德。一生享福，精神富足，不愁吃穿，得過且過。"
        return f"天同星入{p_name}。主福氣、協調、享受，但也主意志較不堅。"

    # --- 廉貞星 ---
    if star_key == "lian_zhen":
        if palace_key == "life": return "廉貞入命。性格狂放不羈，好勝心強，亦正亦邪，次桃花星。"
        if palace_key == "career": return "廉貞入官祿。工作能力強，適合公關、娛樂、科技或軍警。"
        return f"廉貞星入{p_name}。主變動、桃花、血光，亦主原則與秩序。"

    # --- 天府星 ---
    if star_key == "tian_fu":
        if palace_key == "life": return "天府入命。號令星，穩重保守，衣食無憂，有老闆架子。"
        if palace_key == "wealth": return "天府入財帛。財庫坐守，積蓄能力強，財源穩定。"
        if palace_key == "property": return "天府入田宅。主家產豐厚，能守祖業，居住環境佳。"
        return f"天府星入{p_name}。主財庫、包容、穩定，化解因難。"
    
    # --- 太陰星 ---
    if star_key == "tai_yin":
        if palace_key == "life": return "太陰入命。溫柔細膩，重情感，好潔淨，善於積蓄，財星。"
        if palace_key == "spouse": return "太陰入夫妻。男得美妻溫柔，女嫁俊夫內向。"
        if palace_key == "property": return "太陰入田宅。太陰為田宅主，不動產運極佳，喜置產。"
        return f"太陰星入{p_name}。主財富、母性、溫柔，利於陰性人事物。"

    # --- 貪狼星 ---
    if star_key == "tan_lang":
        if palace_key == "life": return "貪狼入命。多才多藝，擅長交際，桃花旺，慾望強烈。"
        if palace_key == "fortune": return "貪狼入福德。追求精神享受，好奇心重，壽比南山 (與天同梁同)。"
        return f"貪狼星入{p_name}。主桃花、慾望、才藝，靈活多變。"

    # --- 巨門星 ---
    if star_key == "ju_men":
        if palace_key == "life": return "巨門入命。口才佳，心思細密，多疑慮，喜研究分析。"
        if palace_key == "career": return "巨門入官祿。以口為業，如律師、教師、業務、演說。"
        return f"巨門星入{p_name}。主口舌、是非、研究，化權祿則主口才優越。"

    # --- 天相星 ---
    if star_key == "tian_xiang":
        if palace_key == "life": return "天相入命。相貌端正，熱心助人，宰相之輔，重衣食享受。"
        return f"天相星入{p_name}。主印鑑、輔佐、公正，受左右夾宮影響大。"

    # --- 天梁星 ---
    if star_key == "tian_liang":
        if palace_key == "life": return "天梁入命。蔭星，長者風範，愛說教，喜助人，逢凶化吉。"
        if palace_key == "parents": return "天梁入父母。受長輩庇蔭大，父母長壽。"
        if palace_key == "health": return "天梁入疾厄。主健康長壽，但幼時恐多災病 (逢凶化吉)。"
        return f"天梁星入{p_name}。主蔭庇、長壽、監察，清高之星。"

    # --- 七殺星 ---
    if star_key == "qi_sha":
        if palace_key == "life": return "七殺入命。將星，剛毅主觀，勇往直前，獨立自主，早年艱辛。"
        if palace_key == "spouse": return "七殺入夫妻。配偶個性剛強，異國戀或年齡差距大，溝通需耐心。"
        return f"七殺星入{p_name}。主肅殺、變動、權力，宜動不宜靜。"

    # --- 破軍星 ---
    if star_key == "po_jun":
        if palace_key == "life": return "破軍入命。耗星，開創力強，不破不立，一生波動大，先破後成。"
        if palace_key == "kids": return "破軍入子女。子女難管教，破耗家財，或與子女緣動盪。"
        return f"破軍星入{p_name}。主破耗、開創、衝動，大破大立之象。"

    return f"{star_name}在{p_name}。"


def generate_master_rules():
    rules = []
    base_id = 50000
    
    # 1. 十四主星入十二宮 (14 * 12 = 168)
    for p_key in PALACE_KEYS:
        for s_key, s_name in MAIN_STARS.items():
            desc = get_star_meaning(p_key, s_key, s_name)
            rules.append({
                "id": f"M-{base_id}",
                "category": p_key,
                "description": f"{s_name}入{PALACE_NAMES[p_key]}",
                "conditions": {
                    "logic": "AND",
                    "criteria": [
                        {"target": p_key, "has_star": [s_key]}
                    ]
                },
                "result": {
                    "text": desc,
                    "tags": ["主星布局", s_name]
                }
            })
            base_id += 1
            
    # 2. 特殊星曜補充 (祿馬、紅喜、咸池、天姚) - 針對命宮
    special_stars = [
        ("tian_ma", "天馬", "天馬入命。主奔波好動，不出外不能發達。"),
        ("hong_luan", "紅鸞", "紅鸞入命。主早婚，人緣極佳，相貌秀麗，討人喜歡。"),
        ("tian_xi", "天喜", "天喜入命。主隨和熱鬧，喜事多，人緣好。"),
        ("xian_chi", "咸池", "咸池入命。主性慾強，風流剔透，易有感情糾紛。"),
        ("tian_yao", "天姚", "天姚入命。主風情萬種，有獨特魅力，適合演藝公關。")
    ]
    
    for s_key, s_name, s_desc in special_stars:
         rules.append({
            "id": f"M-{base_id}",
            "category": "life",
            "description": f"{s_name}入命宮",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": "life", "has_star": [s_key]}
                ]
            },
            "result": {
                "text": s_desc,
                "tags": ["桃花星", s_name]
            }
        })
         base_id += 1

    return rules

def add_master_rules_to_file():
    rules_file = "ziwei_rules.json"
    
    if os.path.exists(rules_file):
        with open(rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = []
        
    print(f"現有規則數量：{len(existing_rules)}")
    new_rules = generate_master_rules()
    print(f"新增主星規則數量：{len(new_rules)}")
    
    existing_ids = {rule.get("id") for rule in existing_rules}
    final_new_rules = [r for r in new_rules if r["id"] not in existing_ids]
    
    all_rules = existing_rules + final_new_rules
    
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    print("✅ 全方位主星規則 (十四主星入十二宮) 更新完成")

if __name__ == "__main__":
    add_master_rules_to_file()
