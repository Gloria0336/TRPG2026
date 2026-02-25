from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base
# 為了建立關聯，我們也可以直接用字串指定或是延遲載入 (Lazy loading)，
# 這裡使用字串指定，讓 SQLAlchemy 處理依賴關係

# 關聯表：角色與天賦 (多對多)
character_talent_table = Table(
    'character_talents', Base.metadata,
    Column('character_id', Integer, ForeignKey('characters.id'), primary_key=True),
    Column('talent_id', Integer, ForeignKey('talents.id'), primary_key=True)
)

class Character(Base):
    """角色主要狀態"""
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True) # 對應真實玩家登入帳號，若單機可忽略
    name = Column(String(50), nullable=False)
    
    class_id = Column(Integer, ForeignKey("classes.id"))
    current_node_id = Column(Integer, ForeignKey("map_nodes.id")) # 當前位置
    
    # 基礎屬性 (6圍)
    strength = Column(Integer, default=5)    # 力量
    agility = Column(Integer, default=5)     # 敏捷
    intellect = Column(Integer, default=5)   # 智力
    perception = Column(Integer, default=5)  # 感知
    charisma = Column(Integer, default=5)    # 魅力
    technique = Column(Integer, default=5)   # 技巧
    
    # 衍伸數值 (狀態)
    max_hp = Column(Integer, default=100)
    current_hp = Column(Integer, default=100)
    max_mp = Column(Integer, default=50)
    current_mp = Column(Integer, default=50)
    hunger = Column(Integer, default=0)      # 飢渴值 (0~100)
    thirst = Column(Integer, default=0)
    
    # 劇情進度 (用 JSON 彈性儲存)
    story_flags = Column(String, default="{}") # e.g. '{"met_npc_a": true, "boss_1_killed": false}'
    
    # 關聯
    talents = relationship("app.models.system.Talent", secondary=character_talent_table)
    custom_skills = relationship("PlayerCustomSkill", back_populates="character")

class PlayerCustomSkill(Base):
    """玩家自定義的技能表現 (重點)"""
    __tablename__ = "player_custom_skills"
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    template_id = Column(Integer, ForeignKey("system_skills.id")) # 綁定數值底層
    
    # 玩家自創內容
    custom_name = Column(String(50))         # e.g. "漆黑之炎" (底層可能是火球術)
    custom_description = Column(String(200)) # "從深淵召喚的毀滅之火..."
    vfx_color = Column(String(20))           # 表現效果代碼
    
    character = relationship("Character", back_populates="custom_skills")
    template = relationship("app.models.system.SystemSkillTemplate")
