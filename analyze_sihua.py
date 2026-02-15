"""
宮干四化分析工具
=================
此工具用於分析命盤中所有宮位的宮干四化情況，包括：
1. 自化：宮干化出的四化星在本宮
2. 飛化：宮干化出的四化星飛入其他宮
3. 來化：其他宮的宮干化星飛入本宮
"""

import json
from rule_engine import SI_HUA_TABLE, STAR_MAP, PALACE_NAMES, create_chart_from_dict

# 反向映射：從星曜英文key找中文名
STAR_NAME_MAP = STAR_MAP

# 四化中文名稱
SIHUA_NAMES = {
    "hua_lu": "化祿",
    "hua_quan": "化權", 
    "hua_ke": "化科",
    "hua_ji": "化忌"
}

def analyze_palace_sihua(chart, palace):
    """
    分析單一宮位的四化情況
    
    Returns:
        {
            "palace_name": "命宮",
            "stem": "甲",
            "self_hua": [...],  # 自化列表
            "flying_out": [...], # 飛出列表
            "flying_in": [...]   # 飛入列表
        }
    """
    result = {
        "palace_name": palace.name,
        "palace_key": palace.key,
        "index": palace.index,
        "stem": palace.stem,
        "self_hua": [],
        "flying_out": [],
        "flying_in": []
    }
    
    if not palace.stem or palace.stem not in SI_HUA_TABLE:
        return result
    
    # 獲取該宮干的四化表
    sihua_table = SI_HUA_TABLE[palace.stem]
    
    # 分析四化情況
    for trans_key, star_key in sihua_table.items():
        star_name = STAR_NAME_MAP.get(star_key, star_key)
        trans_name = SIHUA_NAMES.get(trans_key, trans_key)
        
        # 查找該星在哪個宮位
        target_palace = None
        for p in chart.palaces:
            if p.has_star(star_key):
                target_palace = p
                break
        
        if target_palace:
            info = {
                "type": trans_key,
                "type_name": trans_name,
                "star": star_key,
                "star_name": star_name,
                "target_palace": target_palace.name,
                "target_index": target_palace.index
            }
            
            # 判斷是自化還是飛化
            if target_palace.index == palace.index:
                # 自化：化星在本宮
                result["self_hua"].append(info)
                info["desc"] = f"{palace.name}宮干【{palace.stem}】使{star_name}自化{trans_name}"
            else:
                # 飛化：化星飛入其他宮
                result["flying_out"].append(info)
                info["desc"] = f"{palace.name}宮干【{palace.stem}】的{trans_name}飛入{target_palace.name}（{star_name}）"
    
    return result

def analyze_chart_sihua(chart):
    """
    分析整張命盤的四化情況
    """
    results = []
    
    for palace in chart.palaces:
        palace_result = analyze_palace_sihua(chart, palace)
        results.append(palace_result)
    
    # 計算飛入（來化）
    for palace in chart.palaces:
        palace_idx = palace.index
        palace_result = results[palace_idx]
        
        # 檢查其他宮位飛出的四化
        for other_palace in chart.palaces:
            if other_palace.index == palace_idx:
                continue
            
            other_result = results[other_palace.index]
            for flying_out in other_result["flying_out"]:
                if flying_out["target_index"] == palace_idx:
                    flying_in_info = flying_out.copy()
                    flying_in_info["from_palace"] = other_palace.name
                    flying_in_info["from_index"] = other_palace.index
                    flying_in_info["desc"] = f"{other_palace.name}的{flying_out['type_name']}飛入本宮（{flying_out['star_name']}）"
                    palace_result["flying_in"].append(flying_in_info)
    
    return results

def print_sihua_report(results):
    """
    打印四化分析報告
    """
    print("\n" + "="*80)
    print("                         宮干四化完整分析報告")
    print("="*80 + "\n")
    
    for result in results:
        palace_name = result["palace_name"]
        stem = result["stem"] if result["stem"] else "無"
        
        print(f"\n【{palace_name}】（宮干：{stem}）")
        print("-" * 70)
        
        # 自化
        if result["self_hua"]:
            print("\n  ✨ 自化：")
            for item in result["self_hua"]:
                print(f"     • {item['desc']}")
        
        # 飛出
        if result["flying_out"]:
            print("\n  ➡️  飛化出宮：")
            for item in result["flying_out"]:
                print(f"     • {item['desc']}")
        
        # 飛入
        if result["flying_in"]:
            print("\n  ⬅️  飛化入宮：")
            for item in result["flying_in"]:
                print(f"     • {item['desc']}")
        
        if not result["self_hua"] and not result["flying_out"] and not result["flying_in"]:
            print("  （本宮無宮干四化相關事項）")
    
    print("\n" + "="*80)
    print("                              報告結束")
    print("="*80 + "\n")

def generate_sihua_rules(results):
    """
    根據四化分析結果，生成可用的規則建議
    """
    suggestions = []
    
    for result in results:
        palace_key = result["palace_key"]
        palace_name = result["palace_name"]
        
        # 自化規則建議
        for self_hua in result["self_hua"]:
            trans_key = self_hua["type"]
            star_name = self_hua["star_name"]
            
            suggestion = {
                "description": f"{palace_name}{self_hua['type_name']}（{star_name}自化{self_hua['type_name']}）",
                "rule_type": "self_transformation",
                "condition": {
                    "target": palace_key,
                    "self_trans": trans_key,
                    "has_star": self_hua["star"]
                },
                "interpretation": f"{palace_name}出現{star_name}自化{self_hua['type_name']}，表示..."
            }
            suggestions.append(suggestion)
        
        # 飛化規則建議
        for flying_in in result["flying_in"]:
            trans_key = flying_in["type"]
            from_palace = results[flying_in["from_index"]]["palace_key"]
            
            suggestion = {
                "description": f"{flying_in['from_palace']}的{flying_in['type_name']}飛入{palace_name}",
                "rule_type": "flying_transformation",
                "condition": {
                    "target": palace_key,
                    "flying_from": from_palace,
                    "trans": trans_key
                },
                "interpretation": f"{flying_in['from_palace']}的{flying_in['type_name']}飛入{palace_name}，表示..."
            }
            suggestions.append(suggestion)
    
    return suggestions

def main():
    """
    主程序：從 user_records.json 讀取最新的命盤數據進行分析
    """
    import os
    
    print("\n正在載入命盤資料...")
    
    # 嘗試從 user_records.json 讀取
    if os.path.exists("user_records.json"):
        with open("user_records.json", "r", encoding="utf-8") as f:
            records = json.load(f)
        
        if records:
            print(f"找到 {len(records)} 筆記錄，使用最新的一筆進行分析...\n")
            latest_record = records[-1]
            print(f"分析對象：{latest_record.get('name', '未知')}")
            print(f"生日：{latest_record.get('birth_date', '未知')}")
            print(f"性別：{latest_record.get('gender', '未知')}")
    
    # 這裡需要實際的 chart_data，暫時使用測試資料
    print("\n[注意] 目前需要完整的命盤數據（chart_data）才能進行分析")
    print("請在實際使用時，從前端獲取完整的命盤 JSON 數據\n")
    
    # 示例：創建測試命盤
    print("="*80)
    print("以下是宮干四化分析工具的使用說明：")
    print("="*80)
    print("""
使用方法：
---------
1. 從前端獲取完整的命盤數據（chartData）
2. 使用 create_chart_from_dict() 創建 Chart 對象
3. 調用 analyze_chart_sihua() 進行分析
4. 使用 print_sihua_report() 打印報告

示例代碼：
---------
from analyze_sihua import analyze_chart_sihua, print_sihua_report
from rule_engine import create_chart_from_dict

# chart_data 是從前端獲取的 JSON 數據
chart = create_chart_from_dict(chart_data, gender="M")
results = analyze_chart_sihua(chart)
print_sihua_report(results)

# 獲取規則建議
suggestions = generate_sihua_rules(results)
for s in suggestions:
    print(s)
    """)
    
    print("\n宮干四化對照表：")
    print("-" * 80)
    for stem, trans_map in SI_HUA_TABLE.items():
        lu = STAR_NAME_MAP.get(trans_map["hua_lu"], "?")
        quan = STAR_NAME_MAP.get(trans_map["hua_quan"], "?")
        ke = STAR_NAME_MAP.get(trans_map["hua_ke"], "?")
        ji = STAR_NAME_MAP.get(trans_map["hua_ji"], "?")
        print(f"{stem}干：化祿-{lu}  化權-{quan}  化科-{ke}  化忌-{ji}")
    print("-" * 80)

if __name__ == "__main__":
    main()
