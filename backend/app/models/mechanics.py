"""
戰鬥與判定邏輯 (Combat Engine & Mechanics)
"""

def calculate_damage(base_dmg: int, skill_scaling: float, attacker_stats: dict, defender_stats: dict) -> int:
    """計算技能實際造成的傷害，考慮六圍加成與防禦"""
    # 範例結構：根據屬性與技能底層運算傷害
    # 例如，吃到攻擊者的 intellect 智力加成
    bonus = attacker_stats.get("intellect", 5) * skill_scaling
    
    # 假設防禦方每 2 點技術 (technique) 可以減免 1 點傷害
    defense_reduction = defender_stats.get("technique", 5) // 2
    
    final_damage = int((base_dmg + bonus) - defense_reduction)
    return max(1, final_damage) # 至少造成 1 點傷害

