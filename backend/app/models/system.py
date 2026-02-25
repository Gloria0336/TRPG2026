"""
system.py — 系統設定層
包含：職業 / 職業等級加成 / 天賦 / 系統技能範本
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ClassInfo(Base):
    """職業設定（提供轉職用）"""

    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)         # "念動力者", "武裝狂徒", "暗影行者"
    description = Column(Text)
    # 可轉職的目標職業 id 列表，JSON 字串
    # e.g. "[3, 5]" 表示可轉職到 id=3 或 id=5 的職業
    can_promote_to_json = Column(Text, default="[]")
    # 職業基礎屬性加成（開局時套用）
    base_stat_bonus_json = Column(Text, default="{}")
    # e.g. '{"strength": 2, "intellect": 5}' 念動力者智力+5

    level_bonuses = relationship("ClassLevelBonus", back_populates="class_info")


class ClassLevelBonus(Base):
    """職業每個等級的屬性成長公式"""

    __tablename__ = "class_level_bonuses"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    level = Column(Integer, nullable=False)     # 幾級時觸發
    # 等級提升時的屬性加成，JSON 字串
    # e.g. '{"max_hp": 10, "max_mp": 5, "intellect": 1}'
    stat_bonus_json = Column(Text, nullable=False)
    # 是否在此等級解鎖新技能
    unlock_skill_id = Column(Integer, ForeignKey("system_skills.id"), nullable=True)

    class_info = relationship("ClassInfo", back_populates="level_bonuses")
    unlock_skill = relationship("SystemSkillTemplate")


class Talent(Base):
    """天賦設定（開局選定後不能修改）"""

    __tablename__ = "talents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(Text)
    effect_type = Column(String(50))  # buff_stat / unique_passive / skill_modifier
    # 效果數值，JSON 字串
    # e.g. '{"stat": "strength", "value": 3}' 或 '{"multiply_damage": 1.2}'
    effect_json = Column(Text, default="{}")
    # 被動觸發條件（若為空則為永久加成）
    # e.g. '{"trigger": "on_low_hp", "threshold": 0.3}'
    condition_json = Column(Text, nullable=True)


class SystemSkillTemplate(Base):
    """
    系統技能範本（決定真實數值，玩家可在此基礎上包裝自定義外觀）
    skill_type: active / passive / reaction
    """

    __tablename__ = "system_skills"

    id = Column(Integer, primary_key=True, index=True)
    base_name = Column(String(50))               # "火球術", "念動衝擊", "快速閃避"
    description = Column(Text)
    skill_type = Column(String(20), default="active")  # active/passive/reaction
    base_damage = Column(Integer, default=0)
    cooldown_sec = Column(Float, default=5.0)    # 即時制冷卻時間（秒）
    cost_mp = Column(Integer, default=0)
    cost_hp = Column(Integer, default=0)         # 部分技能消耗生命
    scaling_stat = Column(String(20))            # 主要吃哪個屬性（"intellect", "strength" 等）
    scaling_ratio = Column(Float, default=1.0)   # 屬性加成係數
    is_aoe = Column(Boolean, default=False)      # 是否為範圍技能
    range_type = Column(String(20), default="single")  # single/aoe/self/ally
