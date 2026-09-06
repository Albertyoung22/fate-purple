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


# 十天干四化飛星規則表
SI_HUA_TABLE = {
    '甲': {'lu': '廉貞', 'quan': '破軍', 'ke': '武曲', 'ji': '太陽'},
    '乙': {'lu': '天機', 'quan': '天梁', 'ke': '紫微', 'ji': '太陰'},
    '丙': {'lu': '天同', 'quan': '天機', 'ke': '文昌', 'ji': '廉貞'},
    '丁': {'lu': '太陰', 'quan': '天同', 'ke': '天機', 'ji': '巨門'},
    '戊': {'lu': '貪狼', 'quan': '太陰', 'ke': '右弼', 'ji': '天機'},
    '己': {'lu': '武曲', 'quan': '貪狼', 'ke': '天梁', 'ji': '文曲'},
    '庚': {'lu': '太陽', 'quan': '武曲', 'ke': '太陰', 'ji': '天同'},
    '辛': {'lu': '巨門', 'quan': '太陽', 'ke': '文曲', 'ji': '文昌'},
    '壬': {'lu': '天梁', 'quan': '紫微', 'ke': '左輔', 'ji': '武曲'},
    '癸': {'lu': '破軍', 'quan': '巨門', 'ke': '太陰', 'ji': '貪狼'}
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

# =========================================================================
# 宗師深度性格剖析字典庫 (Deep Human Fortune Teller Master Profiling)
# =========================================================================
STAR_DEEP_PROFILES = {
    "紫微": {
        "nature": "天生自帶威儀與王者格局，自尊心極強，重視個人尊嚴與社會評價，具開創統籌之領袖氣度。",
        "mindset": "凡事講求大局與長遠，不甘居於人下，討厭被瑣碎細節綁架，喜歡站在制高點統禦與定奪決策。",
        "inner": "外表看似莊重沉穩、能扛大任，實則內心孤傲且背負沉重責任感，極度渴望被真心認可，偶有「高處不勝寒」的孤獨心境。",
        "blind_spot": "容易耳軟聽好話、死要面子活受罪，遇挫折不願輕易示弱低頭，有時過於剛愎自用而忽視基層細節。",
        "stress_reaction": "壓力大時會展現更強的掌控欲與威權感，獨攬責任，將焦慮深鎖心底而不願對外求助。",
        "strengths": ["天生領袖魄力與大局掌控力", "極強的抗壓定力與自律風骨", "具備凝聚各方資源的號召力"],
        "growth_lesson": "學會放下身段、懂得授權與傾聽真言，接納自己的脆弱，方能成就真正的仁德之君。",
        "career_vibe": "企業負責人、高階決策者、獨立創業者、品牌主理人、政經要職。"
    },
    "天機": {
        "nature": "心思機敏細膩，應變神速，智慧過人，天生帶有軍師謀略與數理研究之靈氣，求知慾極為旺盛。",
        "mindset": "擅長邏輯分析、推演預測與策劃佈局，行事講求效率與方法，對新事物與技術有極高敏銳度。",
        "inner": "外表斯文隨和、善於溝通協調，內心實則思緒千迴百轉、多思多慮，常處於大腦高速運轉的緊繃狀態，難以真正徹底放鬆。",
        "blind_spot": "容易精神內耗、鑽牛角尖，常因計劃過於完美而在執行時猶豫不決（想得多、做時患得患失），缺乏一貫到底的頑強耐力。",
        "stress_reaction": "遇壓力時容易失眠、神經衰弱或反覆推翻既定方案，陷入自我懷疑的思維迷宮。",
        "strengths": ["卓越的策略推演與問題拆解力", "極快的新知識吸收與轉化速度", "靈活應變、見招拆招的謀略天賦"],
        "growth_lesson": "知行合一，多做少思。學會「放過大腦、沉澱心神」，以七成把握即果斷執行，切莫讓完美主義拖垮進度。",
        "career_vibe": "軟體資訊架構師、數據科學家、策略顧問、行銷企劃大腦、專業研發專家。"
    },
    "太陽": {
        "nature": "光明磊落，熱忱仗義，博愛好施，胸襟開朗開闊，自帶如陽光般溫暖且具感染力的公眾影響力。",
        "mindset": "講求公道正義與奉獻價值，樂於提攜他人、替人解難，行事積極主動，渴望發光發熱獲得社會榮譽。",
        "inner": "對外永遠展現陽光堅強、報喜不報憂的一面，將所有委屈與疲憊深藏，夜深人靜時常因付出得不到同等回報而心生落寞與孤獨。",
        "blind_spot": "愛管閒事、好勝心切，常為了維護面子打腫臉充胖子，容易招惹無端是非口舌，或因輕信他人而吃虧背鍋。",
        "stress_reaction": "壓力大時容易暴躁急進、說話過於直率刺人，或是過度燃燒自己以證明自身價值。",
        "strengths": ["強大的公眾演說與人脈感染力", "無私助人的俠義之風與貴人緣", "勇於承擔責任的陽光正能量"],
        "growth_lesson": "學會「留力愛己，量力而施」。不需要當所有人的救世主，懂得設立邊界與拒絕他人，方能持久發光。",
        "career_vibe": "公眾人物、大眾傳播、跨國貿易、國際外交、教育推廣、能源與文創領航者。"
    },
    "太陰": {
        "nature": "心思縝密，溫柔含蓄，富同理心與藝術審美直覺，具備深思熟慮的耐性與細水長流之財富智慧。",
        "mindset": "重視安全感與穩定秩序，行事謀定而後動，善於觀察細節與他人情緒變化，具備卓越的置產與守財本領。",
        "inner": "外表平靜柔和、謙遜低調，內心世界極其敏感豐富且多愁善感，對人際關係中的冷淡或變動極易產生不安與自我懷疑。",
        "blind_spot": "容易把委屈與不滿憋在心裡形成暗耗，遇衝突傾向逃避冷戰，對金錢與居所有過度焦慮，偶爾過於優柔寡斷。",
        "stress_reaction": "遭遇壓力或情感挫折時，會退回自己的保護殼中默默流淚或瘋狂整理打掃，容易陷入情緒低潮。",
        "strengths": ["敏銳深刻的情感洞察與同理共鳴", "卓越的不動產置產與長線理財天賦", "精緻的審美品味與細膩執行力"],
        "growth_lesson": "學會「勇敢表達真實需求，脫離情緒內耗」。建立內在的安全感錨點，明白不完美也是生活的一種美好。",
        "career_vibe": "房地產投資代銷、財務資產管理、室內美學設計、文化創意作家、心理諮商與高階特助。"
    },
    "武曲": {
        "nature": "正財將星，剛毅果決，講求誠信與原則，做事乾脆俐落、雷厲風行，重實質效益不尚虛浮空談。",
        "mindset": "實事求是，注重邏輯、數據與實體產出。凡事親力親為，相信「一分耕耘一分收穫」，具備極強的生存戰鬥力。",
        "inner": "外表耿直嚴肅、看似不近人情，內心實則赤誠單純、極重情義，只是笨拙於言辭表達與甜言蜜語，常被人誤解為冷酷。",
        "blind_spot": "說話過於直截了當易得罪人，性格過剛易折，遇困難習慣一個人咬牙死扛而不願向人示弱求援，缺乏柔軟彈性。",
        "stress_reaction": "壓力大時會將自己封閉在繁重工作與體力勞動中，情緒緊繃，容易因瑣事動怒或生硬對抗。",
        "strengths": ["無可匹敵的執行力與落地實踐天賦", "冷靜務實的財務管理與生財嗅覺", "一諾千金、值得性命相托的誠信風骨"],
        "growth_lesson": "學會「以柔克剛，外圓內方」。說話留三分餘地，接納人性的多樣與不完美，適度示弱往往能贏得更多支持。",
        "career_vibe": "金融高管、會計精算師、實業製造業老闆、軍警法務、高科技工程主管、外科名醫。"
    },
    "天同": {
        "nature": "福星坐守，溫和敦厚，和藹可親，富赤子之心與幽默感，人緣極佳，天生具備化解矛盾的和氣磁場。",
        "mindset": "崇尚自然隨緣、享受生活樂趣，重視人際和睦與內心愉悅，不喜與人爭名奪利，擅長在合作中營造溫馨氛圍。",
        "inner": "外表看似樂天知命、無憂無慮，內心其實極度渴望被深愛與被呵護，害怕孤獨與衝突，偶爾對未來缺乏安全感。",
        "blind_spot": "容易安於現狀、得過且過，缺乏開創新局的霸氣與狼性，遇到困難容易退縮或依賴他人，有拖延傾向。",
        "stress_reaction": "壓力大時會透過吃喝玩樂、追劇放空來逃避現實問題，直到最後一刻才被動應對。",
        "strengths": ["極佳的親和力與貴人逢凶化吉之運", "調和團隊氣氛、化干戈為玉帛的和諧力", "懂得享受生活、知足常樂的豁達心境"],
        "growth_lesson": "學會「走出舒適圈，逼自己堅強獨立」。將溫柔轉化為堅定的內在力量，主動承擔責任，福報方能化為實質成就。",
        "career_vibe": "文創休閒產業、餐飲美饌主理人、幼兒教育、心理社工、公關協調、旅遊觀光引領者。"
    },
    "廉貞": {
        "nature": "次桃花兼具事業雄心，聰明敏銳，自尊極高，公關手腕高超，是非分明，具備強烈的求勝慾望與獨特審美品味。",
        "mindset": "善於洞察人性弱點與權力結構，行事講求原則與格調，對目標執著堅定，具備極強的政治直覺與開拓魄力。",
        "inner": "外表風趣優雅、處事八面玲瓏，內心其實防衛心極重、愛恨分明且眼裡容不下一粒沙子，一旦遭遇背叛便永不原諒。",
        "blind_spot": "個性過於剛烈執拗，容易因猜忌疑心而產生人際摩擦，在感情或職場權力鬥爭中容易陷入偏執與極端。",
        "stress_reaction": "壓力大時容易鑽進牛角尖，產生強烈的攻擊性或冷酷防禦，甚至不惜玉石俱焚。",
        "strengths": ["卓越的公關交際與資源整合能力", "敏銳的政治敏感度與精準決策魄力", "極高品味的美感與創新突破力"],
        "growth_lesson": "學會「難得糊塗，包容瑕疵」。水至清則無魚，對人對己多一份寬容與留白，方能化煞為權、海納百川。",
        "career_vibe": "科技創新高管、法務律師、精密工程師、醫學美容主理人、時尚藝術設計師、高階公關顧問。"
    },
    "天府": {
        "nature": "南斗令星，庫存充盈，厚重穩健，雍容大度，天生具備管理者風範與守成聚富之本領，行事深謀遠慮。",
        "mindset": "講求實效、風險控管與長線收益，不打無準備之仗，善於建立制度、管理團隊與積蓄資產，重信譽與條理。",
        "inner": "外表寬宏大度、談笑風生，內心算盤其實打得極其精細，對個人利益與資產安全有極強的防護意識，不輕易交心。",
        "blind_spot": "容易保守自封、缺乏大刀闊斧的冒險精神，有時過於講究排場享受，給人好面子、算計過深的距離感。",
        "stress_reaction": "壓力大時會更加嚴格控管資源、緊縮防線，變得固執保守，甚至用物質享受來轉移壓力。",
        "strengths": ["穩健宏大的資產管理與聚財守庫力", "建立秩序、運籌帷幄的組織領導天賦", "處變不驚的從容定力與深厚福氣"],
        "growth_lesson": "學會「敢於適度冒險，擁抱變革創新」。在守成之餘大膽開闢新賽道，方能讓財庫能量成倍翻滾。",
        "career_vibe": "金融銀行高管、房產地產巨擘、大型企業財務長/執行長、資產管理專家、實業領袖。"
    },
    "貪狼": {
        "nature": "第一桃花與多才多藝之曜，靈活百變，善交際應酬，好奇心旺盛，具強烈的冒險精神與生命慾望驅動力。",
        "mindset": "思維不受常規束縛，善於捕捉潮流趨勢與人性慾望，行事隨機應變、善借東風，具極強的跨界整合天賦。",
        "inner": "外表風趣幽默、八面玲瓏、善於活躍氣氛，內心深處卻常有一股莫名的空虛感與對玄學、哲理超脫的嚮往（半仙半俗）。",
        "blind_spot": "貪多嚼不爛，容易三分鐘熱度，在金錢、慾望與情感誘惑面前容易動搖，缺乏長期的專注與耐性。",
        "stress_reaction": "壓力大時容易透過過度社交、消費或冒險投機來尋找刺激，情緒容易在狂熱與冷漠之間劇烈擺盪。",
        "strengths": ["無與倫比的社交魅力與資源鏈接天賦", "對市場商機與新興趨勢的敏銳嗅覺", "多才多藝、隨時能東山再起的強大適應力"],
        "growth_lesson": "學會「克制慾望，專注深耕」。將百般才藝聚焦於一兩個核心賽道，由巧入拙、厚積薄發，必成大器。",
        "career_vibe": "新興創投經理人、公關演藝經紀、自媒體領袖、醫美休閒連鎖、跨界創業家、國際商務談判官。"
    },
    "巨門": {
        "nature": "暗曜是非與洞察之星，辯才無礙，心思縝密深邃，天生具備批判思維與追根究底的求真精神。",
        "mindset": "凡事講求證據與邏輯推演，善於發現事物背後的漏洞與隱患，對虛偽表象有極強的免疫力與拆穿本領。",
        "inner": "外表耿直敢言、防衛性強甚至顯得有些挑剔，內心深處其實極度渴望被全然信任與理解，極度重承諾但害怕受傷受騙。",
        "blind_spot": "說話直接一針見血容易刺痛他人、招惹口舌是非，多疑猜忌心重，容易將人際關係搞得過度緊張緊繃。",
        "stress_reaction": "壓力大時會開啟「辯論防禦模式」，言語犀利刻薄，或將自己封閉在深層懷疑中反覆糾結。",
        "strengths": ["深刻入微的洞察力與邏輯剖析天賦", "口若懸河、一言九鼎的專業表達與說服力", "嚴謹把關、防範風險的監察本領"],
        "growth_lesson": "學會「修口德，多讚賞少挑剔」。良言一句三冬暖，將銳利言詞轉化為溫暖智慧的指引，化暗為明。",
        "career_vibe": "知名執業律師、企業戰略諮詢師、專業培訓名師、醫藥科研專家、法務風控總監、資深評論家。"
    },
    "天相": {
        "nature": "宰相印璽之星，端莊斯文，處事圓融周到，講求誠信與契約精神，極富同情心與服務輔佐熱忱。",
        "mindset": "重視秩序、美感與形象名譽，善於協調各方矛盾、平衡利益關係，是天生的最佳夥伴與高階幕僚操盤手。",
        "inner": "外表溫文儒雅、大方得體，內心極為在意他人的評價與眼光，常因想要面面俱到而讓自己活得非常心累。",
        "blind_spot": "缺乏獨立開創的決斷魄力，容易隨波逐流（逢吉則吉、逢凶則凶），在重大抉擇面前容易優柔寡斷被身邊人左右。",
        "stress_reaction": "壓力大時容易委曲求全、過度討好他人，壓抑自己的真實感受，導致內心失衡焦慮。",
        "strengths": ["高超的人際協調與跨部門整合能力", "無懈可擊的職業操守與值得信賴的形象", "細緻入微的執行輔助與公眾溝通天賦"],
        "growth_lesson": "學會「堅持自我主見，敢於立威拒絕」。確立清晰的個人邊界，不再做老好人，方能成為獨當一面的定海神針。",
        "career_vibe": "企業特助核心副手、人力資源總監、品牌公關操盤手、高級行政主管、連鎖加盟管理大師。"
    },
    "天梁": {
        "nature": "蔭星壽相，老成持重，正氣凜然，具長者風範與慈悲心腸，喜照顧庇蔭弱小，遇難常有逢凶化吉之神效。",
        "mindset": "重視道德倫理、原則規矩與社會責任，行事穩妥周全，具備深厚的長遠眼光與化解危機之智慧。",
        "inner": "外表威嚴沉穩、受人敬重，內心其實有一股孤高清流的堅持，偶有「好為人師」的說教傾向，承擔過多他人因果而勞心。",
        "blind_spot": "過於固執保守、自命清高，容易倚老賣老或強加自身價值觀於他人，往往「先經歷波折磨礪後方得蔭庇」。",
        "stress_reaction": "壓力大時會展現更強的道德說教與冷淡態度，把自己當作受苦受難的長者，獨自承受風雨。",
        "strengths": ["遇難成祥、逢凶化吉的強大福報庇護", "受人敬仰的公正聲望與道德號召力", "長遠佈局、穩如泰山的危機處理本領"],
        "growth_lesson": "學會「順應時代，放下執念」。尊重年輕一代的自由選擇，不強行干預他人命運，自身福澤方能悠遠流長。",
        "career_vibe": "醫學中醫大家、司法審判官員、長照醫療高管、宗教公益領袖、企業倫理風控長、資深學術泰斗。"
    },
    "七殺": {
        "nature": "將星威權，雄心萬丈，勇猛剛毅，敢作敢當，具開疆拓土之魄力與不屈不撓之鋼鐵意志，天生的孤膽英雄。",
        "mindset": "目標導向極強，雷厲風行，勇於打破舊秩序、開創新局面，不畏艱難險阻，喜歡在競爭激烈的戰場中證明自己。",
        "inner": "外表冷峻嚴肅、霸氣外露、令人敬畏，內心其實深藏極重的情義與難以言說的深層孤獨，習慣將所有傷痛化為前進的燃料。",
        "blind_spot": "急躁衝動，獨斷專行，行事過於剛猛不留退路，容易在人際關係中硬碰硬而四處樹敵，人生起伏波動較大。",
        "stress_reaction": "壓力大時會化身戰鬥狂人，不惜代價發動猛攻，甚至盲目冒險推進，容易陷入孤注一擲的險境。",
        "strengths": ["無所畏懼的拓荒魄力與殺伐決斷之勇", "在絕境中逆風翻盤、東山再起的強韌生命力", "卓越的戰略突破力與單兵作戰能力"],
        "growth_lesson": "學會「剛柔並濟，謀定而後動」。收斂鋒芒，善用團隊力量，給自己留有緩衝餘地，方能成就不世功業。",
        "career_vibe": "新市場業務拓荒統帥、重大工程總指揮、軍警武職高官、外科權威手術專家、獨立創業先鋒。"
    },
    "破軍": {
        "nature": "先鋒革新之宿，破舊立新，敢破敢立，反叛常規，具強大的破壞性創新能力，不甘平庸，勇於歸零重來。",
        "mindset": "厭惡墨守成規與體制束縛，思維跳躍前衛，善於在混亂中尋找顛覆性機會，敢於砸碎舊壇子重鑄新世界。",
        "inner": "外表特立獨行、風風火火、愛恨極其分明，內心情感波濤洶湧，對認定的人與事一往無前，但極易因失望而徹底斬斷關係。",
        "blind_spot": "情緒起伏極大，行事易走極端，喜新厭舊，容易在衝動之下把一手好牌打散，人生常經歷大起大落的洗牌。",
        "stress_reaction": "壓力大時會產生強烈的「毀滅重建衝動」，索性破罐破摔或推翻一切重新開始，行事令人捉摸不透。",
        "strengths": ["顛覆傳統、引領潮流的突破性創新力", "大刀闊斧、破除萬難的魄力與執行勇氣", "不怕重頭再來的超凡心理韌性"],
        "growth_lesson": "學會「破而後立，立重於破」。在破除舊體制前先想好建設方案，修練耐性與情緒穩定度，方能功成圓滿。",
        "career_vibe": "創新科技破局者、創投顛覆領袖、物流供應鏈變革操盤手、拆除重建大師、前衛藝術家、變革型CEO。"
    }
}

FU_DEEP_PROFILES = {
    "紫微": "內心自視甚高，精神世界追求崇高與尊貴，重視心靈品味，不願與庸俗同流，但常有深層的精神孤獨感。",
    "天機": "大腦常年難以止息，精神世界充滿各種哲思、推演與想像，靈性悟性極高，但易陷精神焦慮與神經內耗。",
    "太陽": "心靈追求光明正大與奉獻感，樂觀豁達，喜好宏大敘事，但常因精神承擔過重而感到心力交瘁。",
    "太陰": "精神世界極度細膩敏銳，富詩意與審美情趣，重情感滋養，但容易多愁善感、受月令與環境氛圍牽動情緒。",
    "武曲": "內心務實堅毅，精神寄託在實質成就與物質底氣上，不喜無病呻吟，但情感世界較為乾涸，需主動培養情趣。",
    "天同": "福德正位，天生具備懂得放鬆、知足常樂的心靈療癒力，精神世界浪漫純真，能自得其樂，福慧綿長。",
    "廉貞": "心靈世界極具張力，慾望與精神超脫相互拉扯，追求極致的美感與獨特性，情感熱烈但易陷情執與偏執。",
    "天府": "內心悠閒從容、精神世界富足安適，懂得調適生活壓力，重視精神與物質享受的雙重平衡，心寬體胖。",
    "貪狼": "精神世界充滿好奇與探索慾望，對哲學、玄學、佛道或神秘體驗有天生靈性直覺，心靈在世俗與出世間擺盪。",
    "巨門": "內心深處多疑善思，精神世界防線森嚴，對人性常持審慎觀望態度，需尋得能全然交心的心靈知己。",
    "天相": "精神追求和諧、優雅與被認同，重視精神體面與生活儀式感，但容易受外在人際氛圍影響內心安寧。",
    "天梁": "老成清高，具宗教哲理與天地大道的宿世善根，精神世界超脫世俗名利，樂善好施，心靈境界悠遠。",
    "七殺": "內心剛烈孤傲，精神世界如同孤獨的獨行俠，崇尚力量與突破，習慣獨自舔舐心靈傷口，極少向人傾訴。",
    "破軍": "精神世界充滿冒險與狂熱，不安於現狀，內心渴望波瀾壯闊的人生體驗，情緒起伏劇烈但具強大爆發力。"
}

BODY_DEEP_PROFILES = {
    "命宮": "【命身同宮】：三十歲後性格與初衷高度一致，行事風格表裡如一，具備極強的主見與定力，不為外境所動，一生全靠自我硬實力開拓天地。",
    "官祿宮": "【身寄官祿】：三十歲後人生重心全力聚焦於事業事功與專業威望，渴望在社會上立下不世基業，工作成就感直接決定人生幸福高度。",
    "事業宮": "【身寄事業】：三十歲後人生重心全力聚焦於事業事功與專業威望，渴望在社會上立下不世基業，工作成就感直接決定人生幸福高度。",
    "財帛宮": "【身寄財帛】：三十歲後行事極重財務安全感與實質投資回報，注重資源變現與資產護城河，善於將各項機緣轉化為真金白銀。",
    "夫妻宮": "【身寄夫妻】：三十歲後人生深受感情生活與伴侶互動牽引，極度渴望溫暖和睦的家庭歸宿，伴侶的支持是人生最大的前進動力。",
    "遷移宮": "【身寄遷移】：三十歲後喜動不喜靜，出外拓展、跨界交流或異鄉打拼往往能激發出遠超原地的潛能，人脈越廣、運勢越隆。",
    "福德宮": "【身寄福德】：三十歲後格外重視內心精神的自由與生活品質，善於調養身心，不願為追逐名利而犧牲自我內心的平靜安寧。"
}

# =========================================================================
# 經典雙星同宮複合性格與化學反應字典庫 (Dual-Star Personality Chemistry)
# =========================================================================
DUAL_STAR_PROFILES = {
    ("紫微", "天府"): {
        "title": "【紫府同宮 · 帝王坐庫格】",
        "desc": "紫微之尊貴遇天府之穩重，格局宏大而氣度沉穩。你天生具備大將之風與強大組織管理本能，既有領袖開創野心，又懂精打細算守成聚庫。外表寬厚雍容，內心極具謀略與原則，不輕易涉險，為典型的富貴大器之相。"
    },
    ("紫微", "貪狼"): {
        "title": "【紫貪同宮 · 桃花帝王格】",
        "desc": "紫微之高貴融合貪狼之靈動才藝，性格多才多藝、極富個人魅力與公關手腕。善於在名利場中遊刃有餘，物質享受與精神求道兼備（半仙半俗）。外表風趣圓融，骨子裡自尊心極強，中年後若能專注深耕，必成行業領軍人物。"
    },
    ("紫微", "天相"): {
        "title": "【紫相同宮 · 君臣慶會格】",
        "desc": "紫微帝王得天相印璽相助，斯文得體、做事極具條理與誠信原則。為人重公道名譽，善於協調複雜人際矛盾，是極佳的高階核心掌舵者。唯有時過於在意他人評價與表面體面，需適度放下包袱。"
    },
    ("紫微", "七殺"): {
        "title": "【紫殺同宮 · 將相開疆格】",
        "desc": "紫微之威權化為七殺之利刃，霸氣外露、雄心萬丈，具極強的殺伐決斷魄力與開疆拓土意志。不服輸、不低頭，越是逆境越能激發出驚人的戰鬥力。一生多波折歷練，但每經一次考驗便脫胎換骨一次。"
    },
    ("紫微", "破軍"): {
        "title": "【紫破同宮 · 帝王變革格】",
        "desc": "紫微之尊與破軍之反叛交織，性格敢破敢立、勇於打破舊秩序。思維不受傳統框架束縛，具強烈的顛覆性創新能力。一生常經歷大起大落之轉折，但能在廢墟上建立起獨屬於自己的嶄新王國。"
    },
    ("武曲", "天府"): {
        "title": "【武府同宮 · 巨富蓄庫格】",
        "desc": "正財星遇庫星，財氣與守財力均達頂點。為人務實穩重、誠信守諾，算盤打得極精卻不失大氣。做事一步一腳印，極具商業頭腦與資產嗅覺，為長線積蓄、中年後必致巨富的紮實格局。"
    },
    ("武曲", "貪狼"): {
        "title": "【武貪同宮 · 晚發大器格】",
        "desc": "武曲之剛毅務實融合貪狼之靈活欲望，具備「少年辛勤多磨礪，中年厚積薄發」之經典特質。早年奔波歷練、嘗試多元，三十五歲後情商與商業嗅覺雙雙成熟，爆發力極強，財藝雙收。"
    },
    ("武曲", "天相"): {
        "title": "【武相同宮 · 正氣實幹格】",
        "desc": "剛正武曲得圓融天相調和，外圓內方、剛柔並濟。行事雷厲風行又注重契約制度與夥伴信賴，既能親自操刀落地，又能運籌帷幄協調資源，深受長官與夥伴敬重。"
    },
    ("武曲", "七殺"): {
        "title": "【武殺同宮 · 鋼鐵將星格】",
        "desc": "兩大金性剛星匯聚，剛毅無比、鐵面無私，具備超凡的執行魄力與抗壓耐力。說話做事直截了當，不喜虛情假意。性格過剛易折，此生最大功課在於學會柔軟與包容，剛柔相濟方能無敵。"
    },
    ("武曲", "破軍"): {
        "title": "【武破同宮 · 破舊生財格】",
        "desc": "武曲正財遇破軍革新，一生求財不走尋常路，善於在變革、技術顛覆或新興領域中搶佔先機。敢於投入、敢於洗牌，早年財運起伏較大，歷練成熟後能開闢出源源不絕的全新財源。"
    },
    ("廉貞", "天府"): {
        "title": "【廉府同宮 · 經緯理財格】",
        "desc": "廉貞之敏銳野心結合天府之穩健城府，具備極強的政治智慧與資產佈局能力。進退有據、城府深沉，善於在複雜局面中保持不敗之地，為高階管理與策略投資的大才。"
    },
    ("廉貞", "貪狼"): {
        "title": "【廉貪同宮 · 絕世靈動格】",
        "desc": "兩大桃花星曜同宮，極富藝術靈感、公關魅力與敏銳的人性洞察力。善於活躍氣氛、捕捉商機，靈動百變。此生需注意情慾與金錢誘惑，若能將才華聚焦於事業，成就非凡。"
    },
    ("廉貞", "天相"): {
        "title": "【廉相同宮 · 剛正謀略格】",
        "desc": "廉貞之剛直得天相之印信調和，為人公道正派、是非分明，極具責任感與公眾服務熱忱。善於制定規則、把關風控，是不可多得的定海神針型人才。"
    },
    ("廉貞", "七殺"): {
        "title": "【廉殺同宮 · 雄才大略格】",
        "desc": "剛烈果敢、目標極其明確，具備強大的開拓進取心與冒險精神。行事乾脆俐落、不拖泥帶水，勇於承擔極限挑戰，在艱苦複雜的環境中特別能展現英豪本色。"
    },
    ("廉貞", "破軍"): {
        "title": "【廉破同宮 · 變革破局格】",
        "desc": "聰明敏銳且反叛常規，對不合理現狀有強烈顛覆衝動。思維前衛跳躍，在科技創新、商業重組中往往能扮演關鍵破局者，敢愛敢恨、個性鮮明。"
    },
    ("天機", "太陰"): {
        "title": "【機陰同宮 · 探花深謀格】",
        "desc": "智慧天機與縝密太陰相生，心思極度細膩敏銳，記憶力與策略推演能力超群。擅長策劃、分析、幕僚諮詢與文字藝術。外表文雅謙和，內心多思多慮，需防範過度精神內耗。"
    },
    ("天機", "巨門"): {
        "title": "【機巨同宮 · 機變辯才格】",
        "desc": "智慧遇口才，反應神速、舌戰群儒，具備超凡的邏輯批判力與演說才能。擅長洞察破綻、解決疑難雜症。口直心快容易招惹是非，學會修口德、少挑剔即是開運關鍵。"
    },
    ("天機", "天梁"): {
        "title": "【機梁同宮 · 神機妙算格】",
        "desc": "謀略天機得蔭星天梁加持，智慧老成、深謀遠慮，具極高的宗教哲理悟性與逢凶化吉之福澤。為人樂善好施、善於為人解難排憂，在專業諮詢、醫藥學術界備受推崇。"
    },
    ("太陽", "太陰"): {
        "title": "【日月同宮 · 陰陽調和格】",
        "desc": "陽光熱忱與月曜細膩兼備，性格多面立體，既有博愛仗義的公眾影響力，又有體貼入微的情感洞察。行事日夜操勞、親力親為，一生多得男女貴人相助，名利雙收。"
    },
    ("太陽", "巨門"): {
        "title": "【巨日同宮 · 照暗生輝格】",
        "desc": "太陽陽光驅散巨門暗晦，化暗為明，具備強大的公眾說服力與開拓感染力。善於透過口才傳播、國際貿易、跨界合作揚名立萬，越是遠離家鄉或面向公眾越能發光發熱。"
    },
    ("太陽", "天梁"): {
        "title": "【陽梁同宮 · 日照雷門格】",
        "desc": "熱忱光明結合正氣慈悲，具極強的道德威望與長者風範。重視原則公道，利於考運功名、司法醫療與文教傳播，為人受人敬仰，遇難必有逢凶化吉之大福報。"
    },
    ("天同", "太陰"): {
        "title": "【同陰同宮 · 溫婉水德格】",
        "desc": "兩大水星交融，性情溫婉優雅、富有詩意與生活品味。人緣極好、貴人運旺，懂得享受生活、知足常樂。外表隨和，內心富同理心，唯在重大抉擇時需加強主見與魄力。"
    },
    ("天同", "巨門"): {
        "title": "【同巨同宮 · 溫厚言辯格】",
        "desc": "天同之溫厚調和巨門之銳利，談吐幽默風趣而富有哲理，擅長在人際溝通中化解尷尬。內心情感豐富但容易有隱秘思慮，學會坦誠溝通、放下疑慮，人生自得安樂。"
    },
    ("天同", "天梁"): {
        "title": "【同梁同宮 · 壽福相蔭格】",
        "desc": "福星與蔭星同宮，一生福報深厚、逢凶化吉。為人善良寬厚、樂善好施，具長壽安康之相。行事不喜與人爭鋒，常在不知不覺中化解危機、坐享清福。"
    }
}

# =========================================================================
# 化忌落宮因果執念與深層心靈功課 (Ji Star Karmic Lessons)
# =========================================================================
JI_PALACE_LESSONS = {
    "命宮": "【化忌坐命宮】：自我要求嚴苛，容易自我懷疑與精神內耗，總覺得自己不夠好。此生最大功課在於「全然接納自己、放下完美主義」，寬恕過去方能釋放內在無限潛能。",
    "兄弟宮": "【化忌在兄弟宮】：重情重義卻易在手足、合夥人間吃虧背鍋，借貸需謹慎。此生功課在於「親兄弟明算帳，劃清金錢邊界」，不以金錢綁架情感。",
    "夫妻宮": "【化忌在夫妻宮】：情執深重，對感情付出極深卻容易患得患失、疑心生暗鬼。此生功課在於「學會彼此留白、不把伴侶當作全部安全感來源」，以平常心相待方能白頭偕老。",
    "子女宮": "【化忌在子女宮】：為子女晚輩操心過度，代溝或牽掛較深。此生功課在於「學會適時放手，信任孩子有其自身造化」，多引導少控制，福澤自然綿長。",
    "財帛宮": "【化忌在財帛宮】：對財務有強烈的匱乏焦慮感，常為金錢勞心傷神。此生功課在於「看淡得失，以專業生財替代投機盲賭」，守住現金流，明白知足即是富足。",
    "疾厄宮": "【化忌在疾厄宮】：身心易因長期勞碌而累積暗耗，需注意臟腑調養與情緒排毒。此生功課在於「學會休養生息、傾聽身體警訊」，不過度透支元神。",
    "遷移宮": "【化忌在遷移宮（沖命宮）】：出外奔波常感孤獨辛勞，人際防備心重。此生功課在於「出門在外謀定而後動，少爭口舌是非」，以謙遜低調化解暗箭。",
    "奴僕宮": "【化忌在奴僕宮（交友位）】：真心待人卻容易遇人不淑、遭背後議論背刺。此生功課在於「擇友而交，事上見真章言上留三分」，不對非知心之人過度交心。",
    "官祿宮": "【化忌在官祿宮（事業位）】：工作狂熱、責任感沉重，常將職場問題攬在自己肩上導致壓力爆棚。此生功課在於「學會工作與生活平衡，懂得團隊分工」，事業方能長久長青。",
    "田宅宮": "【化忌在田宅宮】：極度在乎家庭秩序與房產安全感，為家事瑣事操勞。此生功課在於「營造祥和包容的家庭氛圍，不在瑣碎細節上苛求家人」，家和萬事興。",
    "福德宮": "【化忌在福德宮】：潛意識思慮過重，容易鑽牛角尖、失眠焦慮，難以享受當下。此生功課在於「修持正念、冥想靜心，學會活在當下」，心寬則天地皆寬。",
    "父母宮": "【化忌在父母宮】：與長輩觀念易有隔閡或為雙親健康憂心。此生功課在於「以順承溫和化解代溝，孝親積福」，多陪伴關懷，自得祖德暗中庇佑。"
}

# =========================================================================
# 大限交接期（換大運前後）陣痛與心理調適指引 (Decade Transition Insights)
# =========================================================================
DECADE_TRANSITION_INSIGHTS = {
    "active": "緣主目前年齡正處於「舊大限即將交卷、新大限即將啟航」的大運交接樞紐期（轉折年）。此時期心境容易產生『舊賽道乏味、新方向未明』的迷惘與焦慮陣痛，乃命運能量重新洗牌之正常現象。切忌在焦慮中倉促作出重大冒險決策，宜以『沉澱復盤、盤點核心資產、養精蓄銳』為首要方針，從容迎接下一輪大運之騰飛！",
    "stable": "緣主目前正處於當前十年大限的中軸發力期，氣場相對平穩凝聚，各項計畫正按部就班推進，宜乘勝追擊、聚焦深耕。"
}


class FateCPSATSolver:
    """
    Google OR-Tools CP-SAT 命理約束規劃求解器
    """
    def __init__(self, chart_data=None, user_info=None, prompt="", matched_rules=None):
        if isinstance(chart_data, dict):
            self.raw_chart_dict = chart_data
            self.chart_data = chart_data.get("palaces", chart_data.get("chartData", []))
            self.user_info = user_info or {k: v for k, v in chart_data.items() if k not in ("palaces", "chartData")}
        else:
            self.raw_chart_dict = {}
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

    # =========================================================================
    # 深度性格分析與未來命運預測核心引擎 (Master Personality & Future Engine)
    # =========================================================================
    def _analyze_personality_depth(self):
        """全方位深度解析緣主之真實性格、表裡反差、心靈世界與性格盲點"""
        ming = self._extract_palace("命宮")
        body_palace_name = self._get_body_palace()
        body = self._extract_palace(body_palace_name)
        fu = self._extract_palace("福德宮")
        
        # 提取命宮核心主星
        clean_ming_stars = [s.split('(')[0].strip() for s in ming["main_stars"]]
        primary_star = clean_ming_stars[0] if clean_ming_stars else "天機"
        star_info = STAR_DEEP_PROFILES.get(primary_star, STAR_DEEP_PROFILES["天機"])
        
        # 雙主星同宮化學反應深度解析
        multi_star_note = ""
        if len(clean_ming_stars) >= 2:
            s1, s2 = clean_ming_stars[0], clean_ming_stars[1]
            dual = DUAL_STAR_PROFILES.get((s1, s2)) or DUAL_STAR_PROFILES.get((s2, s1))
            if dual:
                multi_star_note = f"\n   - **雙星合璧化學反應**：{dual['title']} {dual['desc']}"
            else:
                sec_star = clean_ming_stars[1]
                sec_info = STAR_DEEP_PROFILES.get(sec_star, {})
                if sec_info:
                    multi_star_note = f"同時盤中會合【{sec_star}】，兼具「{sec_info.get('nature', '')[:35]}...」之雙重潛質，使你兼具剛柔兩種維度，適應力極強。"
                
        # 福德宮內心世界
        clean_fu_stars = [s.split('(')[0].strip() for s in fu["main_stars"]]
        fu_primary = clean_fu_stars[0] if clean_fu_stars else primary_star
        fu_inner_desc = FU_DEEP_PROFILES.get(fu_primary, "內心世界深沉內斂，常有不足為外人道的思慮與對精神安寧的渴望。")
        
        # 身宮後天行事
        body_desc = BODY_DEEP_PROFILES.get(body_palace_name, BODY_DEEP_PROFILES["命宮"])
        
        # 全盤偵測化忌所在宮位與因果功課
        ji_palace_name = ""
        ji_karmic_lesson = ""
        for p in self.chart_data:
            p_name = p.get("palaceName", "")
            stars = p.get("stars", [])
            for s in stars:
                s_name = s.get("name", "") if isinstance(s, dict) else str(s)
                if "忌" in s_name or "化忌" in s_name:
                    for std_p in PALACE_STANDARD:
                        if std_p in p_name:
                            ji_palace_name = std_p
                            break
                    if not ji_palace_name:
                        ji_palace_name = p_name
                    break
            if ji_palace_name:
                break
        
        if ji_palace_name and ji_palace_name in JI_PALACE_LESSONS:
            ji_karmic_lesson = JI_PALACE_LESSONS[ji_palace_name]
        else:
            ji_karmic_lesson = JI_PALACE_LESSONS["命宮"]

        # 煞星與吉星之性格塑形
        sha_impact = []
        if any("擎羊" in s for s in ming["sha_stars"]):
            sha_impact.append("帶【擎羊】：性格多了一股銳利剛猛之衝勁，遇事敢說敢做，但容易急躁動怒，說話過直傷人。")
        if any("陀羅" in s for s in ming["sha_stars"]):
            sha_impact.append("帶【陀羅】：行事深具磨功與韌性，但容易暗中糾結、猶豫不決，遇心結不易快速釋懷。")
        if any("火星" in s or "鈴星" in s for s in ming["sha_stars"]):
            sha_impact.append("帶【火星/鈴星】：反應敏捷具爆發力，性子較急，喜速戰速決，情緒來得快去得也快。")
        if any("地空" in s or "地劫" in s for s in ming["sha_stars"]):
            sha_impact.append("帶【地空/地劫】：思維天馬行空、不落俗套，具超脫哲思與藝術直覺，但對物質得失較為隨興。")
        if any("化忌" in s for s in ming["sha_stars"]):
            sha_impact.append("命宮坐【化忌】：責任心極強且自我要求嚴苛，容易精神內耗、鑽牛角尖，需學會放過自己。")
            
        sha_desc = " ".join(sha_impact) if sha_impact else "命宮星脈純和，少見暴烈煞星相侵，待人處事溫潤持重、富有包容力。"

        return {
            "primary_star": primary_star,
            "nature": star_info["nature"],
            "mindset": star_info["mindset"],
            "inner": star_info["inner"],
            "blind_spot": star_info["blind_spot"],
            "stress_reaction": star_info["stress_reaction"],
            "strengths": star_info["strengths"],
            "growth_lesson": star_info["growth_lesson"],
            "career_vibe": star_info["career_vibe"],
            "multi_star_note": multi_star_note,
            "fu_inner_desc": fu_inner_desc,
            "body_desc": body_desc,
            "sha_desc": sha_desc,
            "ji_palace_name": ji_palace_name,
            "ji_karmic_lesson": ji_karmic_lesson
        }

    def _predict_future_trajectories(self, age):
        """全方位推演緣主未來十年大限、未來數年流年歲運與關鍵人生節點"""
        ming = self._extract_palace("命宮")
        cai = self._extract_palace("財帛宮")
        guan = self._extract_palace("官祿宮")
        qian = self._extract_palace("遷移宮")
        fu = self._extract_palace("福德宮")
        
        # 1. 十年大限計算
        decade_start = (age // 10) * 10 + (2 if age % 10 >= 2 else -8)
        decade_end = decade_start + 9
        next_decade_start = decade_end + 1
        next_decade_end = next_decade_start + 9
        
        # 大限核心主題
        decade_theme = "事業奠基與專業突破" if age <= 35 else "資產聚富與格局擴張" if age <= 50 else "名望收穫與安享福慧"
        
        # 大限交接期心理陣痛與調適指引
        years_in_decade = age - decade_start
        if years_in_decade >= 8 or years_in_decade <= 1:
            transition_advice = DECADE_TRANSITION_INSIGHTS["active"]
        else:
            transition_advice = DECADE_TRANSITION_INSIGHTS["stable"]

        # 2. 未來流年推演 (2024 甲辰, 2025 乙巳, 2026 丙午, 2027 丁未, 2028 戊申)
        flow_years_data = [
            {
                "year": 2024,
                "gan_zhi": "甲辰年",
                "tag": "【青龍革新 · 破立之年】",
                "action": "★ 宜積極進取、開創新局 ★",
                "sihua": "廉貞化祿、破軍化權、武曲化科、太陽化忌",
                "desc": "此年天干甲木引動廉貞之祿與破軍之權，乃大刀闊斧打破舊體制、跨界嘗試新賽道之良機。唯太陽化忌，須注意人際溝通切莫好勝逞強，防範為他人做嫁衣或因面子問題破耗資財。"
            },
            {
                "year": 2025,
                "gan_zhi": "乙巳年",
                "tag": "【靈蛇聚智 · 策略轉型之年】",
                "action": "★ 宜深耕專業、知識變現 ★",
                "sihua": "天機化祿、天梁化權、紫微化科、太陰化忌",
                "desc": "天機化祿與天梁化權交馳，智慧財產、技術專利與專業顧問能力最能轉化為實質回報，長輩貴人運旺。太陰化忌提醒需特別注意不動產契約細節，感情與內心需防範焦慮內耗。"
            },
            {
                "year": 2026,
                "gan_zhi": "丙午年",
                "tag": "【紅炎生輝 · 人脈合夥之年】",
                "action": "★ 宜廣結善緣、借力使力 ★",
                "sihua": "天同化祿、天機化權、文昌化科、廉貞化忌",
                "desc": "天同化祿帶來豐厚的人際福報與生活享受，文昌化科利於名聲傳播、考照進修與品牌建立。廉貞化忌提醒在公關合作與契約簽署時務必黑白分明，切莫感情用事以防惹上合約糾紛。"
            },
            {
                "year": 2027,
                "gan_zhi": "丁未年",
                "tag": "【玉兔藏金 · 蓄庫沉澱之年】",
                "action": "★ 宜守成理財、購屋置產 ★",
                "sihua": "太陰化祿、天同化權、天機化科、巨門化忌",
                "desc": "太陰化祿入庫，乃資產沉澱、購置不動產與穩健理財之黃金豐收年，家庭資產厚實。巨門化忌提醒日常言語多留餘地，莫捲入職場是非口舌，低調悶聲發大財最為吉利。"
            }
        ]
        
        # 3. 未來四大維度里程碑節點預測
        milestones = {
            "career": f"在 {decade_start+2}～{decade_start+5} 歲期間迎來職場位階之重大躍升或獨立主導核心專案的黃金窗口；此時宜主動爭取帶兵打仗，奠定不可動搖之行業地位。",
            "wealth": f"在流年逢「化祿/祿存」之大年（特別是逢乙、丁、己干之年）將迎來資產倍增與投資紅利；逢「化忌/空劫」之年切忌盲目擴張與高槓桿借貸，守住現金流即是贏家。",
            "love": "感情世界將隨大限福德與夫妻宮轉動而漸入佳境；已有伴侶者需在事業衝刺期給予彼此充足的心靈陪伴，未婚者在流年鸞喜吉星引動之年（逢辰、巳、午年）極易邂逅正緣。",
            "health": f"五行中需長年注意調養命盤最弱之五行臟腑，尤其在每逢換大限（如 {decade_start}、{decade_end} 歲前後）需注意生活作息規律，避免過度勞累透支元神。"
        }
        
        return {
            "decade_start": decade_start,
            "decade_end": decade_end,
            "next_decade_start": next_decade_start,
            "next_decade_end": next_decade_end,
            "decade_theme": decade_theme,
            "transition_advice": transition_advice,
            "flow_years": flow_years_data,
            "milestones": milestones
        }

    def generate_report(self):
        """完整命譜最優化推演解析報告（大師深度命盤解析：結合深度性格剖析與未來運程預測）"""
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
        
        # 取得深度性格與未來預測
        p_info = self._analyze_personality_depth()
        f_pred = self._predict_future_trajectories(age)
        
        report = []
        report.append("【紫微天機道長 · 宗師全盤命譜乾坤精批】")
        report.append("============================================================")
        report.append("● 命盤定格：紫微拱照 · 神煞得位 · 命身福德三位一體")
        report.append("● 氣數周天：十二宮度氣脈貫通，五行生剋有情，天地乾坤定局！")
        report.append("● 宗師評斷：氣骨清奇，有大智大勇之底色，知進退明得失必成大器。\n")

        report.append(f"緣主 {name}（現年 **{age} 歲**，生肖屬**{zodiac}**）：")
        report.append(f"老道凝神為你詳觀命譜，推演十二宮度星曜賦性、三方四正牽連呼應，以及子平八字五行生剋守恆。這張盤氣象端嚴，老道如同在茶桌前與你促膝長談，且聽老道為你層層剖析你的「真實性格底色」與「未來命運軌跡」：\n")

        report.append("### 🧠 一、緣主真實性格與內心世界深度剖析（像真正算命師之摸骨神斷）")
        report.append(f"1. **【先天性格底色與思維架構】**：")
        report.append(f"   - 你的命宮核心坐守【**{p_info['primary_star']}**】。{p_info['nature']}")
        report.append(f"   - **思維與決策模式**：{p_info['mindset']} {p_info['multi_star_note']}")
        report.append(f"2. **【表裡反差與深層心靈世界（福德宮精神透視）】**：")
        report.append(f"   - **外在風貌 vs. 內在心境**：{p_info['inner']}")
        report.append(f"   - **心靈精神寄託**：{p_info['fu_inner_desc']}")
        report.append(f"3. **【人際防禦機制與後天言行作風（身宮與吉煞格局）】**：")
        report.append(f"   - **三十歲後行事轉變**：{p_info['body_desc']}")
        report.append(f"   - **吉星與煞星之激發**：{p_info['sha_desc']}")
        report.append(f"   - **處於壓力下的真實反應**：{p_info['stress_reaction']}")
        report.append(f"4. **【核心天賦長板、性格盲點與深層因果執念】**：")
        report.append(f"   - ★ **三大核心天賦長板**：1. {p_info['strengths'][0]}  2. {p_info['strengths'][1]}  3. {p_info['strengths'][2]}")
        report.append(f"   - ⚠️ **潛在性格盲點**：{p_info['blind_spot']}")
        report.append(f"   - ☸️ **因果執念與深層心靈功課**：{p_info['ji_karmic_lesson']}")
        report.append(f"   - 💡 **宗師破局修心指南**：{p_info['growth_lesson']}\n")

        report.append("### 🔮 二、未來命運軌跡與流年大運深度預測（大師天機推演）")
        report.append(f"1. **【當前十年大限運程推演（{f_pred['decade_start']}～{f_pred['decade_end']} 歲）】**：")
        report.append(f"   - **十年大運核心主題**：★ **{f_pred['decade_theme']}** ★")
        report.append(f"   - **前三年（奠基佈局期）**：重在蓄積能量、打造核心護城河，切莫急於求成，以守為攻。")
        report.append(f"   - **中四年（黃金爆發期）**：三方四正吉星交會，為此十年運勢最高峰，宜大膽把握升遷、跨界或創業良機！")
        report.append(f"   - **後三年（收成固本期）**：資產穩健入庫，注重家庭平衡與健康調養，為下一個大限（{f_pred['next_decade_start']}～{f_pred['next_decade_end']}歲）蓄積動能。")
        report.append(f"   - 🔄 **大限交接與轉折調適指引**：{f_pred['transition_advice']}")
        report.append(f"2. **【未來數年流年歲運走勢預測與吉凶導航】**：")
        for fy in f_pred['flow_years']:
            report.append(f"   - **● {fy['year']} {fy['gan_zhi']} {fy['tag']}**（{fy['action']}）：")
            report.append(f"     - 四化引動：{fy['sihua']}")
            report.append(f"     - 歲運詳批：{fy['desc']}")
        report.append(f"3. **【未來四大核心維度關鍵節點大預測】**：")
        report.append(f"   - 📈 **事業前程**：{f_pred['milestones']['career']}")
        report.append(f"   - 💰 **財富資產**：{f_pred['milestones']['wealth']}")
        report.append(f"   - ❤️ **感情婚姻**：{f_pred['milestones']['love']}")
        report.append(f"   - 🌿 **健康元神**：{f_pred['milestones']['health']}\n")

        report.append("### 📊 三、十二宮位先天能量氣數")
        for p_name, score in self.palace_scores.items():
            bar_len = int(score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            report.append(f"- **{p_name}**: 【{bar}】 {score} 分")
        report.append("")

        report.append("### 🏆 四、大師格局定盤批註")
        report.append(f"1. **命盤最強樞紐位**：【{top_palaces[0][0]}】({top_palaces[0][1]}分)、【{top_palaces[1][0]}】({top_palaces[1][1]}分)、【{top_palaces[2][0]}】({top_palaces[2][1]}分)。")
        report.append(f"   - 此為你命盤中最強盛之「福澤樞紐」，氣場最旺。此生若能依託這三大宮位的優勢領域發展，定能事半功倍、得道多助！")
        report.append(f"2. **需修心安神之位**：【{weak_palace[0]}】({weak_palace[1]}分)。")
        report.append(f"   - 此宮位承受較多星曜磨礪或張力，考驗較多，宜以「靜水流深、以柔克剛」為原則，莫鑽牛角尖。\n")

        report.append("### ☯️ 五、五行中庸平衡與大師趨吉避凶開運錦囊")
        for e_key, e_val in self.element_scores.items():
            report.append(f"- **{ELEMENT_NAMES[e_key]}**: 能量指數 {e_val} / 100")
        report.append(f"\n💡 **大師開運裁定**：緣主命盤最喜【{element_desc}】，宜借天地相生之氣滋養命盤。")
        report.append(f"- **開運吉祥色**：★ **{lucky_color}** ★")
        report.append(f"- **生旺得利吉時**：每日 ★ **{self.best_timing}** ★")
        report.append(f"- **開運迎祥方位**：★ **{self.best_direction}** ★")
        report.append(f"- **適合行業領域**：{p_info['career_vibe']}")
        report.append(f"\n✦ 【老道定心真言】\n『知命者不怨天，知己者不尤人。』明曉自身性情長短，順應天時大運節奏，人生必定海闊天空、福祿壽喜全備！")

        return "\n".join(report)

    # =========================================================================
    # 【核心大師即時諮詢】：命宮、身宮與三方四正深度合參 (Deep Master Consultation)
    # =========================================================================
    def _handle_instant_master_consultation(self, name, clean_q="", prompt=""):
        """大師即時諮詢：深層解析命宮、身宮、三方四正、深度性格剖析與未來運勢預測"""
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
        
        # 命宮主星字串
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
        
        # 取得深度性格分析與未來預測
        p_info = self._analyze_personality_depth()
        f_pred = self._predict_future_trajectories(age)
        
        # 人生階段定義
        if age <= 25:
            stage_desc = "初涉江湖之潛龍蓄勢期。滿懷熱忱，思維靈活，正是博覽廣涉、扎穩專業功底的黃金年華。"
        elif age <= 35:
            stage_desc = "成家立業與事業衝刺之關鍵攀升期。既承載各方期待與職場重任，又面臨生活開銷與賽道定型之抉擇考驗。"
        elif age <= 50:
            stage_desc = "人生事功之頂峰掌舵與厚積薄發期。見慣風浪，深諳世道，重在資源整合、團隊定海與家庭長遠傳承。"
        else:
            stage_desc = "心性通透之甲子圓融期。閱歷深厚，知進退明得失，重在福慧雙修、傳承晚輩與從容頤養。"

        return (
            f"【紫微天機 · 宗師即時深度諮詢開示】：\n\n"
            f"緣主 {name}（現年 **{age} 歲**，生肖屬**{zodiac_str}**）：\n"
            f"老道凝神為你詳觀紫微命譜十二宮度氣脈，推演星曜坐守、三方四正交馳與五行生剋守恆。\n\n"
            f"當前緣主歲數正行至：★ **{stage_desc}** ★\n"
            f"整張命盤氣象端嚴，三方四正交會格局定為：★ **{pattern_desc}** ★。\n"
            f"且聽老道像一位懂你的資深算命師，為你依「性格心靈深處剖析」與「未來命運軌跡大預測」逐層剖析吉凶機關：\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【一、命身福德三位一體 · 緣主真實性格與內心世界深度透視】\n"
            f"● **命宮底色（先天心性）**：坐守地支【**{ming['zhi']}宮**】（底氣 **{ming['score']} 分**），坐守【**{ming_main_str}**】。\n"
            f"  - **個性性格分析**：{p_info['nature']}\n"
            f"  - **思維與決策風格**：{p_info['mindset']} {p_info['multi_star_note']}\n"
            f"● **福德宮（深層內心與精神世界）**：\n"
            f"  - **表裡反差與隱藏心靈**：{p_info['inner']}\n"
            f"  - **潛意識精神世界**：{p_info['fu_inner_desc']}\n"
            f"● **身宮寄託（三十歲後言行風骨）**：寄於【**{body_palace_name}**】（坐守【{body_main_str}】）。\n"
            f"  - **後天行事作風**：{p_info['body_desc']}\n"
            f"  - **吉煞格局激發**：{p_info['sha_desc']}\n"
            f"● **性格天賦與修為功課**：\n"
            f"  - ★ **三大核心天賦**：1. {p_info['strengths'][0]} 2. {p_info['strengths'][1]} 3. {p_info['strengths'][2]}\n"
            f"  - ⚠️ **性格弱點盲點**：{p_info['blind_spot']}\n"
            f"  - ☸️ **因果執念與修心功課**：{p_info['ji_karmic_lesson']}\n"
            f"  - 💡 **大師修心箴言**：{p_info['growth_lesson']}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【二、三方四正 · 氣數周天與功名財氣合參】\n"
            f"● **【財帛宮】（位於{cai['zhi']}宮 · {cai['score']}分）**：坐守【**{cai_main_str}**】。\n"
            f"  - **求財指引**：正財根基雄厚，利於憑藉專業技術、管理謀略或長線佈局生財。切忌高槓桿投機盲賭，穩紮穩打自能聚沙成塔。\n"
            f"● **【官祿宮】（位於{guan['zhi']}宮 · {guan['score']}分）**：坐守【**{guan_main_str}**】。\n"
            f"  - **事業前程**：適合在具備決策權、技術主導性或專業門檻的賽道深耕，不宜在平庸內耗的環境中虛擲光陰。\n"
            f"● **【遷移宮】（位於{qian['zhi']}宮 · {qian['score']}分）**：坐守【**{qian_main_str}**】。\n"
            f"  - **出外際遇**：出外有貴人相助，多向外走動、拓展人脈或跨界學習，格局必能越走越寬。\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【三、未來命運軌跡與十年大限大預測】\n"
            f"● **當前十年大運（{f_pred['decade_start']}～{f_pred['decade_end']} 歲）**：★ **{f_pred['decade_theme']}** ★\n"
            f"  - **前三年（奠基佈局期）**：打穩根基，累積專業與人脈，以守為攻。\n"
            f"  - **中四年（黃金爆發期）**：大限吉星匯聚，為此十年位階攀升與資產倍增之最高峰，宜果斷抓住轉型/晉升機遇！\n"
            f"  - **後三年（收成沉澱期）**：成果固化，資產入庫，為下一輪大限蓄力。\n"
            f"  - 🔄 **大限交接與轉折調適指引**：{f_pred['transition_advice']}\n"
            f"● **未來數年流年歲運吉凶預警**：\n"
            f"  - **2024 甲辰年**：{f_pred['flow_years'][0]['tag']}（{f_pred['flow_years'][0]['action']}）—— {f_pred['flow_years'][0]['desc']}\n"
            f"  - **2025 乙巳年**：{f_pred['flow_years'][1]['tag']}（{f_pred['flow_years'][1]['action']}）—— {f_pred['flow_years'][1]['desc']}\n"
            f"  - **2026 丙午年**：{f_pred['flow_years'][2]['tag']}（{f_pred['flow_years'][2]['action']}）—— {f_pred['flow_years'][2]['desc']}\n"
            f"  - **2027 丁未年**：{f_pred['flow_years'][3]['tag']}（{f_pred['flow_years'][3]['action']}）—— {f_pred['flow_years'][3]['desc']}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【四、未來四大核心領域關鍵節點預測】\n"
            f"● 📈 **事業發展節點**：{f_pred['milestones']['career']}\n"
            f"● 💰 **財富進出節點**：{f_pred['milestones']['wealth']}\n"
            f"● ❤️ **感情婚姻節點**：{f_pred['milestones']['love']}\n"
            f"● 🌿 **健康調養節點**：{f_pred['milestones']['health']}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【五、宗師點撥 · 人生當前關竅與開運錦囊】\n"
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
        # 0. 教學與講堂問答
        if (target_type == "teaching" or
            any(kw in clean_q for kw in ["教學", "怎麼學", "教我", "學習紫微", "飛星原理", "四化口訣", "怎麼看盤", "如何看盤", "排盤原理", "自化是什麼", "什麼是自化", "四化怎麼看", "如何學飛星", "心法口訣"]) or
            any(kw in prompt for kw in ["飛星教學", "紫微教學", "講堂", "傳授心法"])):
            return self._handle_teaching(name, clean_q)

        # 0. 紫微斗數四化飛星術專屬神斷
        if (target_type == "flying" or 
            any(kw in clean_q for kw in ["飛星", "四化", "自化", "化祿入", "化忌入", "化權入", "化科入", "飛入", "飛出", "發射宮", "祿入", "忌入", "飛星術"]) or 
            any(kw in prompt for kw in ["四化飛星", "飛星神斷", "飛星術", "自化分析"])):
            return self._handle_flying_stars(name, clean_q)

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


    def _analyze_flying_stars(self):
        """解析全盤十二宮四化飛星因果牽引矩陣與自化現象"""
        results = []
        palaces_data = self.chart_data if isinstance(self.chart_data, list) else self.chart_data.get('palaces', [])
        if not palaces_data:
            return results

        # 建立星曜 -> 宮位名稱映射
        def find_palace_for_star(star_name):
            for p in palaces_data:
                p_name = p.get('name', '')
                stars = p.get('stars', [])
                for s in stars:
                    s_name = s.get('name', '') if isinstance(s, dict) else str(s)
                    if star_name in s_name:
                        return p_name
            return "外宮"

        for p in palaces_data:
            p_name = p.get('name', '')
            gan = p.get('gan', '')
            zhi = p.get('zhi', '')
            trans = SI_HUA_TABLE.get(gan)
            if not trans:
                continue

            target_lu = find_palace_for_star(trans['lu'])
            target_quan = find_palace_for_star(trans['quan'])
            target_ke = find_palace_for_star(trans['ke'])
            target_ji = find_palace_for_star(trans['ji'])

            self_trans = []
            if target_lu == p_name: self_trans.append("自化祿(" + trans['lu'] + ")")
            if target_quan == p_name: self_trans.append("自化權(" + trans['quan'] + ")")
            if target_ke == p_name: self_trans.append("自化科(" + trans['ke'] + ")")
            if target_ji == p_name: self_trans.append("自化忌(" + trans['ji'] + ")")

            results.append({
                'source': p_name,
                'gan': gan,
                'zhi': zhi,
                'trans': trans,
                'target_lu': target_lu,
                'target_quan': target_quan,
                'target_ke': target_ke,
                'target_ji': target_ji,
                'self_trans': self_trans
            })
        return results


    def _handle_teaching(self, name, clean_q=""):
        """專屬宗師傳道授業 · 紫微斗數排盤與四化飛星講堂"""
        return (
            f"【紫微天機道長 · 紫微斗數與四化飛星講堂開示】：\n\n"
            f"善哉！緣主 {name} 懷求道向學之心，老道欣然為你傳授紫微斗數與四化飛星之核心真諦！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【第一步：明辨體用 · 星為體，化為用】\n"
            f"1. **十四正曜（體）**：乃先天各具稟賦之星宿。如紫微為帝、天機為謀、武曲為財、破軍為革新。\n"
            f"2. **十天干四化（用）**：天干引動四化，乃時空能量流轉之源頭。「星無四化不靈，宮無飛星不動」！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【第二步：十天干四化必背宗師口訣】\n"
            f"● **甲廉破武陽**：廉貞化祿、破軍化權、武曲化科、太陽化忌\n"
            f"● **乙機梁紫陰**：天機化祿、天梁化權、紫微化科、太陰化忌\n"
            f"● **丙同機昌廉**：天同化祿、天機化權、文昌化科、廉貞化忌\n"
            f"● **丁陰同機巨**：太陰化祿、天同化權、天機化科、巨門化忌\n"
            f"● **戊貪陰右機**：貪狼化祿、太陰化權、右弼化科、天機化忌\n"
            f"● **己武貪梁曲**：武曲化祿、貪狼化權、天梁化科、文曲化忌\n"
            f"● **庚陽武陰同**：太陽化祿、武曲化權、太陰化科、天同化忌\n"
            f"● **辛巨陽曲昌**：巨門化祿、太陽化權、文曲化科、文昌化忌\n"
            f"● **壬梁紫輔武**：天梁化祿、紫微化權、左輔化科、武曲化忌\n"
            f"● **癸破巨陰貪**：破軍化祿、巨門化權、太陰化科、貪狼化忌\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【第三步：飛星看盤三步演算法】\n"
            f"1. **看發射宮天干**：如命宮天干為「甲」。\n"
            f"2. **查對應四化星**：甲干使「廉貞化祿、太陽化忌」。\n"
            f"3. **看落入何宮位**：廉貞若在財帛宮，即為「命宮飛祿入財帛」；太陽若在遷移宮，即為「命宮飛忌入遷移」。發射宮為因，落入宮為果！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【第四步：自化與沖照奧秘】\n"
            f"● **自化**：本宮天干引動本宮之星產生化祿或化忌，代表能量的離心與自我釋懷。\n"
            f"● **沖照**：化祿所入之宮，其對宮受「照」（吉氣凝聚）；化忌所入之宮，其對宮受「沖」（考驗與動盪所在）。\n\n"
            f"💡 **老道傳心法言**：\n"
            f"『易道順應自然，算命重在明心。』知命並非宿命，知曉四化飛星之牽引，即可隨祿而動、修忌為智，將命運的主導權掌握於自己手中！"
        )

    def _handle_flying_stars(self, name, clean_q=""):
        """專屬宗師四化飛星因果神斷"""
        flying_matrix = self._analyze_flying_stars()
        ming = self._extract_palace('命宮')
        ming_fly = next((f for f in flying_matrix if f['source'] == '命宮'), None)

        all_self_trans = []
        for f in flying_matrix:
            if f['self_trans']:
                joined_st = '、'.join(f['self_trans'])
                all_self_trans.append(f"{f['source']}【{joined_st}】")

        self_trans_desc = '、'.join(all_self_trans) if all_self_trans else '盤中氣場凝練，少見劇烈自化散氣，能量凝聚度高。'

        # 命宮發射飛星解讀
        if ming_fly:
            ming_trans = ming_fly['trans']
            m_lu_target = ming_fly['target_lu']
            m_ji_target = ming_fly['target_ji']
            m_quan_target = ming_fly['target_quan']
            m_ke_target = ming_fly['target_ke']
            m_gan = ming_fly['gan']
        else:
            m_gan = ming.get('gan', '甲')
            m_lu_target = '財帛宮'
            m_ji_target = '遷移宮'
            m_quan_target = '官祿宮'
            m_ke_target = '福德宮'
            ming_trans = {'lu': '化祿星', 'quan': '化權星', 'ke': '化科星', 'ji': '化忌星'}

        # 飛星因果深度解義
        # 祿之因果
        if m_lu_target == '財帛宮':
            lu_cause = '【命宮化祿入財帛】：先天對金錢有敏銳嗅覺，善於憑藉自身才智開闢財源，求財順遂、財緣深厚。'
        elif m_lu_target in ['官祿宮', '事業宮']:
            lu_cause = '【命宮化祿入官祿】：對工作與事業滿懷熱情，投入即能見成效，職場容易得人緣與貴人提攜。'
        elif m_lu_target == '夫妻宮':
            lu_cause = '【命宮化祿入夫妻】：情深意重，極度疼惜配偶，對婚姻關係具備高度付出精神，樂於照顧伴侶。'
        elif m_lu_target == '田宅宮':
            lu_cause = '【命宮化祿入田宅】：心繫家宅與產業，一生重視置產蓄庫，善於將收益沉澱為不動產，福澤澤被家人。'
        elif m_lu_target == '遷移宮':
            lu_cause = '【命宮化祿入遷移】：出外人緣極佳，異鄉逢貴人，多往外走動或拓展跨界視野，最能引動四方福祿。'
        elif m_lu_target == '命宮':
            lu_cause = '【命宮自化祿】：樂天豁達、心寬體胖，自給自足，但偶有自我滿足或開銷隨興之傾向。'
        else:
            lu_cause = f'【命宮化祿入{m_lu_target}】：緣主先天將福澤與善緣投注於【{m_lu_target}】，在此領域最易獲得成就感與順遂機緣。'

        # 忌之因果
        if m_ji_target == '命宮':
            ji_cause = '【命宮自化忌】：自我要求極高、易陷精神內耗與鑽牛角尖。需修練「放過自己、活在當下」之豁達心法。'
        elif m_ji_target == '遷移宮':
            ji_cause = '【命宮化忌入遷移（沖命宮）】：出外打拼常感辛勞孤獨、壓力沉重；在外言行宜謹慎防小人，凡事謀定而後動。'
        elif m_ji_target == '財帛宮':
            ji_cause = '【命宮化忌入財帛（沖福德）】：一生為財務生計殫精竭慮，對金錢有強烈執念與安全感焦慮，易勞心傷神。'
        elif m_ji_target in ['官祿宮', '事業宮']:
            ji_cause = '【命宮化忌入官祿（沖夫妻）】：工作狂熱或職場責任重，常因全力撲在事業上而忽略了伴侶感受與私生活平衡。'
        elif m_ji_target == '夫妻宮':
            ji_cause = '【命宮化忌入夫妻（沖官祿）】：對感情付出過深反而易生猜疑或情執，感情波折往往牽動事業心境，需學會彼此留白。'
        elif m_ji_target == '田宅宮':
            ji_cause = '【命宮化忌入田宅（沖子女）】：極度在乎家庭責任與房產安全感，日常為家事操勞，對家宅環境有較高掌控欲。'
        else:
            ji_cause = f'【命宮化忌入{m_ji_target}】：此乃緣主此生「因果執念與修行功課」之所在。對【{m_ji_target}】付出極多卻常感心累，唯有看破得失方能破局。'

        return (
            f"【紫微天機道長 · 十二宮四化飛星因果神斷】：\n\n"
            f"老道為緣主 {name} 撥動紫微飛星玄機。所謂「星無四化不靈，宮無飛星不動」，\n"
            f"飛星術乃紫微斗數中推演「起心動念之因」與「吉凶承負之果」最高深之秘法！\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【一、命宮天干發射 · 四化因果牽引線】\n"
            f"緣主命宮坐【{ming['zhi']}宮】，宮干為【**{m_gan}干**】，發動四化飛星貫穿周天：\n"
            f"● 🌸 **化祿入【{m_lu_target}】**（引動【{ming_trans['lu']}】）：\n"
            f"  - **因果玄機**：{lu_cause}\n"
            f"● ⚡ **化權入【{m_quan_target}】**（引動【{ming_trans['quan']}】）：\n"
            f"  - **因果玄機**：你在【{m_quan_target}】展現極強的主導意志與企圖心，行事果斷，勇於扛責。\n"
            f"● 📜 **化科入【{m_ke_target}】**（引動【{ming_trans['ke']}】）：\n"
            f"  - **因果玄機**：在【{m_ke_target}】得清譽與貴人庇蔭，逢凶化吉，以文雅智謀見長。\n"
            f"● 🌀 **化忌入【{m_ji_target}】**（引動【{ming_trans['ji']}】）：\n"
            f"  - **因果玄機**：{ji_cause}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【二、全盤自化現象 · 能量流轉與機緣破立】\n"
            f"● **盤中自化動態**：{self_trans_desc}\n"
            f"💡 **宗師開示**：\n"
            f"自化者，乃各宮天干引動本宮星曜產生離心或向心轉變。自化祿主機緣隨性而來、隨緣而去；自化忌主暗中承擔、自我釋懷。知曉自化，便能知曉何時該進、何時該守。\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【三、宗師點撥 · 飛星破局與解厄心法】\n"
            f"1. **【隨祿而動】**：你命宮化祿直指【{m_lu_target}】，此處乃你今生最大的福報生發點，多將心力投入此處，自能廣納福祿！\n"
            f"2. **【修忌為智】**：化忌落入【{m_ji_target}】，切記「有執念方成忌，放下執念即為菩提」。面對該領域的考驗，切莫鑽牛角尖，順應天道即是破局之道。\n"
            f"3. **【開運天時與方位】**：\n"
            f"   - 調和飛星磁場吉時：每日【**{self.best_timing}**】\n"
            f"   - 迎納祥和紫氣吉方：面朝【**{self.best_direction}**】靜坐調息。\n\n"
            f"✦ 【老道定心真言】\n"
            f"『四化流轉皆為因果，心念一轉天地皆寬。』順應飛星氣脈而行，必能化煞為權、福慧圓滿！"
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
        f_pred = self._predict_future_trajectories(age)
        ming = self._extract_palace("命宮")
        guan = self._extract_palace("官祿宮")
        cai = self._extract_palace("財帛宮")
        return (
            f"【紫微天機道長 · 十年大限運程與未來黃金轉折推演】：\n\n"
            f"老道為緣主 {name} 排演大限命宮（當前正值 **{f_pred['decade_start']}～{f_pred['decade_end']} 歲** 十年大運之關鍵樞紐）：\n\n"
            f"✦ 【一、大限核心定位與總體氣象】\n"
            f"● **十年大運核心主題**：★ **{f_pred['decade_theme']}** ★（命宮底氣 {ming['score']} 分、官祿動能 {guan['score']} 分、財帛氣數 {cai['score']} 分）\n"
            f"● **大運格局透視**：此十年乃你人生承前啟後、由厚積邁向爆發的關鍵樞紐。大運能量逐漸由摸索適應，轉化為建立個人威望與主導權。\n\n"
            f"✦ 【二、十年大限三大階段演進與行動方針】\n"
            f"1. **前三年（{f_pred['decade_start']}～{f_pred['decade_start']+2} 歲 · 奠基紮根期）**：\n"
            f"   - **戰略重點**：重在建立專業護城河、打磨核心技能與積累高質量人脈。切忌盲目浮躁或過早全面擴張，需以守為攻、步步為營。\n"
            f"2. **中四年（{f_pred['decade_start']+3}～{f_pred['decade_start']+6} 歲 · 黃金爆發期）**：\n"
            f"   - **戰略重點**：三方四正吉曜交會生輝，為此十年運勢與位階躍升之最高峰！遇晉升、轉型、合夥或創業契機時，宜大膽搶佔制高點，敢為天下先！\n"
            f"3. **後三年（{f_pred['decade_start']+7}～{f_pred['decade_end']} 歲 · 守成收穫期）**：\n"
            f"   - **戰略重點**：資產穩健入庫與固化為實質資產，注重團隊傳承、家庭和諧與身心調養，為下一個十年大限（{f_pred['next_decade_start']}～{f_pred['next_decade_end']} 歲）蓄滿元氣。\n\n"
            f"✦ 【三、未來四大維度里程碑節點預測】\n"
            f"- 📈 **事業發展節點**：{f_pred['milestones']['career']}\n"
            f"- 💰 **財富進出節點**：{f_pred['milestones']['wealth']}\n"
            f"- ❤️ **感情婚姻節點**：{f_pred['milestones']['love']}\n"
            f"- 🌿 **健康調養節點**：{f_pred['milestones']['health']}\n\n"
            f"💡 **宗師定心提點**：\n"
            f"『大限順天而行，十年一劍霜刃試。』把握中四年的黃金爆發期，該進則進、該守則守，必能開創輝煌基業！"
        )

    def _handle_yearly(self, name):
        age, zodiac_str, _ = self._get_age_and_zodiac()
        f_pred = self._predict_future_trajectories(age)
        
        flow_blocks = []
        for fy in f_pred['flow_years']:
            flow_blocks.append(
                f"● **{fy['year']} {fy['gan_zhi']} {fy['tag']}**（{fy['action']}）\n"
                f"  - **四化引動**：{fy['sihua']}\n"
                f"  - **歲運指南**：{fy['desc']}"
            )
        flows_text = "\n\n".join(flow_blocks)
        
        return (
            f"【紫微天機道長 · 當前及未來數年流年歲運吉凶大預測】：\n\n"
            f"老道為緣主 {name}（現年 **{age} 歲**，生肖屬**{zodiac_str}**）推演太歲行運與十天干四化流轉：\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【未來數年流年歲運精準導航】\n\n"
            f"{flows_text}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【宗師未來歲運進退三大心法】\n"
            f"1. **【擴張年主動出擊】**：逢生旺化祿之年份，切勿猶豫怯縮，主動爭取資源與新項目，乘勢而起。\n"
            f"2. **【防守年沉潛蓄力】**：逢化忌化煞之年份，嚴守現金流與合約細節，少說多做、不爭口舌，即可化險為夷。\n"
            f"3. **【生旺天時吉方】**：日常決策宜選於每日 **{self.best_timing}**，面朝大吉生旺方位【**{self.best_direction}**】納氣安神，定能逢凶化吉、滿載而歸！"
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
        age, zodiac_str, _ = self._get_age_and_zodiac()
        p_info = self._analyze_personality_depth()
        f_pred = self._predict_future_trajectories(age)
        ming = self._extract_palace("命宮")
        top_p = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)[0]
        
        return (
            f"【紫微天機道長 · 緣主深度性格與未來人生指引】：\n\n"
            f"老道以白話通俗之宗師口吻，為緣主 {name}（{age} 歲，屬{zodiac_str}）剖析你的「性情真身」與「未來前程」：\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【一、緣主骨子裡的真實個性與心理特質】\n"
            f"1. **先天性情底色**：你的命宮坐守【**{p_info['primary_star']}**】（底氣 {ming['score']} 分）。{p_info['nature']}\n"
            f"2. **思維與處事風格**：{p_info['mindset']}\n"
            f"3. **表裡反差與內心深處**：{p_info['inner']}（福德宮反映：{p_info['fu_inner_desc']}）\n"
            f"4. **三十歲後的後天追求**：{p_info['body_desc']}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【二、天賦長板、潛在盲點與修心心法】\n"
            f"- ★ **最大優勢樞紐**：坐落於【**{top_p[0]}**】（評分 {top_p[1]} 分），善於在逆境中找出破局之道！\n"
            f"- ★ **核心天賦優勢**：{p_info['strengths'][0]}、{p_info['strengths'][1]}。\n"
            f"- ⚠️ **最需注意之性格盲點**：{p_info['blind_spot']}\n"
            f"- 💡 **大師修心點撥**：{p_info['growth_lesson']}\n\n"
            f"------------------------------------------------------------\n"
            f"✦ 【三、未來十年運程與流年轉折大預測】\n"
            f"● **當前十年大運（{f_pred['decade_start']}～{f_pred['decade_end']} 歲）**：主軸在於「{f_pred['decade_theme']}」，中四年是人生位階晉升與財富擴張之最高峰！\n"
            f"● **未來數年歲運關鍵**：\n"
            f"  - 2024 甲辰年：{f_pred['flow_years'][0]['tag']}，宜積極進取突破。\n"
            f"  - 2025 乙巳年：{f_pred['flow_years'][1]['tag']}，宜深耕專業智慧變現。\n"
            f"  - 2026 丙午年：{f_pred['flow_years'][2]['tag']}，宜借力人脈、防範合約糾紛。\n"
            f"  - 2027 丁未年：{f_pred['flow_years'][3]['tag']}，宜資產沉澱、守成置產。\n\n"
            f"✦ 【老道定心真言】\n"
            f"『認清自己即是智慧，順應天時即是福氣。』放寬心胸，盡人事、順天理，前程自是一片朗然！"
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
        age, zodiac_str, _ = self._get_age_and_zodiac()
        ming = self._extract_palace("命宮")
        body_palace_name = self._get_body_palace()
        p_info = self._analyze_personality_depth()
        f_pred = self._predict_future_trajectories(age)
        top_p = sorted(self.palace_scores.items(), key=lambda x: x[1], reverse=True)[0]
        weak_p = sorted(self.palace_scores.items(), key=lambda x: x[1])[0]
        sorted_elements = sorted(self.element_scores.items(), key=lambda x: x[1])
        weakest = sorted_elements[0][0]
        lucky_color = ELEMENT_COLORS.get(weakest, "玄黑、湛藍、深黛色")

        return (
            f"【紫微天機道長 · 乾坤問津人生解惑】：\n\n"
            f"緣主 {name}（現年 {age} 歲，屬{zodiac_str}）且平心靜氣，聽老道為你觀照當前心境、剖析性情真身與指引未來前程！\n\n"
            f"世事如棋局局新，凡人逢困頓或抉擇時，心亂則神移。老道觀你命宮坐守【**{p_info['primary_star']}**】（底氣 **{ming['score']} 分**），身宮寄託於【**{body_palace_name}**】：\n\n"
            f"✦ 【一、觀照根基 · 性情真身與福澤底色】\n"
            f"1. **你的個性本質**：{p_info['nature']}\n"
            f"2. **表裡心境與內在渴望**：{p_info['inner']}\n"
            f"3. **最強福澤樞紐**：你命盤中最強的支柱在於【**{top_p[0]}**】（底氣 **{top_p[1]} 分**），這代表你先天具備極強的生存智慧與翻盤潛質！眼前之波折迷惘，不過是行至【**{weak_p[0]}**】時的暫時磨礪，絕非終局。\n\n"
            f"✦ 【二、大師指路 · 破除當前盲點與執念】\n"
            f"- ⚠️ **警惕性格陷阱**：{p_info['blind_spot']}\n"
            f"- 💡 **當前破局心法**：針對你心中所念之事，謹記「急則生亂，緩則圓通」。眼前若有猶豫不決之事，莫要逼迫自己在混亂中做重大決定。給自己三至七日靜沉心緒，多聽少動，待局勢明朗後再行定奪。\n\n"
            f"✦ 【三、未來大運轉折與歲運指引】\n"
            f"● **未來十年趨勢（{f_pred['decade_start']}～{f_pred['decade_end']} 歲）**：核心落在「{f_pred['decade_theme']}」，中四年是人生大展鴻圖的黃金窗口！\n"
            f"● **借天時時空轉運**：每日可於 **{self.best_timing}**，面朝你的生旺吉方【**{self.best_direction}**】散步或深思；身著 **{lucky_color}** 系衣飾調和磁場，自能生出澄澈智慧。\n\n"
            f"✦ 【老道定心真言】\n"
            f"『山重水複疑無路，柳暗花明又一村。』天生我材必有用，認清自我長板、順應天時而行，眼前迷霧轉瞬即散，前程定是一片開闊！"
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
