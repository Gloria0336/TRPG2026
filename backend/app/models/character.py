"""
character.py — 角色層
包含：角色主要狀態 / 玩家自定義技能
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from app.database import Base

# 關聯表：角色與天賦（多對多）
character_talent_table = Table(
    "character_talents",
    Base.metadata,
    Column("character_id", Integer, ForeignKey("characters.id"), primary_key=True),
    Column("talent_id", Integer, ForeignKey("talents.id"), primary_key=True),
)


class Character(Base):
    """角色主要狀態"""

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=True)  # 對應玩家帳號，單機可為 null
    name = Column(String(50), nullable=False)

    # 職業（可轉職，儲存當前職業 id）
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    # 當前地圖位置
    current_node_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=True)

    # 等級與經驗
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)

    # 基礎屬性（六圍）
    strength = Column(Integer, default=5)    # 力量
    agility = Column(Integer, default=5)     # 敏捷
    intellect = Column(Integer, default=5)   # 智力
    perception = Column(Integer, default=5)  # 感知
    charisma = Column(Integer, default=5)    # 魅力
    technique = Column(Integer, default=5)   # 技巧

    # 衍伸數值
    max_hp = Column(Integer, default=100)
    current_hp = Column(Integer, default=100)
    max_mp = Column(Integer, default=50)
    current_mp = Column(Integer, default=50)
    hunger = Column(Integer, default=0)      # 飢渴值 0~100（100 = 極度飢餓）
    thirst = Column(Integer, default=0)      # 口渴值 0~100

    # 關聯（使用字串延遲載入，避免循環引入問題）
    class_info = relationship("ClassInfo")
    current_node = relationship("MapNode")
    talents = relationship("Talent", secondary=character_talent_table)
    custom_skills = relationship("PlayerCustomSkill", back_populates="character")
    story_state = relationship("PlayerStoryState", back_populates="character", uselist=False)


class PlayerCustomSkill(Base):
    """
    玩家自定義的技能外觀
    底層數值由 SystemSkillTemplate 決定，玩家可自訂名稱/描述/視覺效果
    """

    __tablename__ = "player_custom_skills"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("system_skills.id"), nullable=False)

    # 玩家自創內容
    custom_name = Column(String(50))          # e.g. "漆黑之炎"（底層是火球術）
    custom_description = Column(Text)         # "從深淵召喚的毀滅之火..."
    vfx_color = Column(String(20))            # 視覺效果代碼，e.g. "#1a0033"
    vfx_style = Column(String(50))            # 粒子風格 key，e.g. "dark_flame", "lightning"

    character = relationship("Character", back_populates="custom_skills")
    template = relationship("SystemSkillTemplate")
