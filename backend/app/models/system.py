from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ClassInfo(Base):
    """職業設定 (提供轉職用)"""
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False) # e.g. "念動力者", "武裝狂徒"
    description = Column(String(200))

class Talent(Base):
    """天賦設定 (開局選定不改)"""
    __tablename__ = "talents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    effect_type = Column(String(50)) # e.g. "buff_str", "unique_passive"
    value = Column(Float)

class SystemSkillTemplate(Base):
    """系統技能範本 (決定真實傷害與CD)"""
    __tablename__ = "system_skills"
    id = Column(Integer, primary_key=True, index=True)
    base_name = Column(String(50))           # 預設名稱：如 "火球術"
    base_damage = Column(Integer, default=10)
    cooldown_sec = Column(Float, default=5.0)# 即時制的重要參數
    cost_mp = Column(Integer, default=5)
    scaling_stat = Column(String(20))        # 傷害吃哪個屬性 (e.g. "intellect")

class MapNode(Base):
    """多層級地圖節點"""
    __tablename__ = "map_nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)    # "廢棄小鎮", "酒館"
    description = Column(String(500))
    node_type = Column(String(50))                # "region", "building", "room"
    
    # Self-Referential (自我關聯) 父節點
    parent_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=True) 
    
    # 關聯：尋找次級區域
    children = relationship("MapNode", backref="parent", remote_side=[id])
