
import json
from rule_engine import create_chart_from_dict, evaluate_rules

# Mock data similar to what fate.html sends
chart_data = [
    {"id": 0, "palaceName": "命宮", "gan": "甲", "zhi": "子", "stars": [{"name": "紫微", "type": "major"}, {"name": "地空", "type": "minor"}]},
    {"id": 1, "palaceName": "兄弟宮", "gan": "乙", "zhi": "丑", "stars": []}
]

chart = create_chart_from_dict(chart_data, gender="M")
rules = [
    {
        "id": "test-1",
        "category": "life",
        "description": "命有地空",
        "conditions": {
            "target": "life",
            "has_star": "di_kong"
        },
        "result": {
            "text": "命帶地空，性格豁達。",
            "tags": ["life"]
        }
    }
]

results = evaluate_rules(chart, rules)
print(f"Matched Results: {json.dumps(results, ensure_ascii=False, indent=2)}")
