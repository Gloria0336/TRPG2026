"""
world.py — 世界建構層
包含：多層級地圖節點 / 節點通道 / 場景事件
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class MapNode(Base):
    """
    多層級地圖節點（Self-Referential）
    層級範例：region → area → building → room
    e.g. 廢棄城市 → 工業區 → 廢棄工廠 → 地下倉庫
    """

    __tablename__ = "map_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)       # "廢棄工廠"
    description = Column(Text)                       # 場景描述文字
    node_type = Column(String(20), nullable=False)   # region/area/building/room
    danger_level = Column(Integer, default=1)        # 1~5，影響隨機事件生成
    is_safe_zone = Column(Boolean, default=False)    # 安全區不會隨機觸發戰鬥
    image_key = Column(String(100), nullable=True)   # 前端對應的場景圖片 key

    # Self-Referential 父節點
    parent_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=True)
    children = relationship("MapNode", backref="parent", remote_side=[id])

    # 場景可觸發的事件
    events = relationship("SceneEvent", back_populates="map_node")

    # 作為起點的連接
    connections_from = relationship(
        "NodeConnection",
        foreign_keys="NodeConnection.from_node_id",
        back_populates="from_node",
    )
    # 作為終點的連接
    connections_to = relationship(
        "NodeConnection",
        foreign_keys="NodeConnection.to_node_id",
        back_populates="to_node",
    )


class NodeConnection(Base):
    """
    節點之間的通道（有向圖）
    可設定單向或雙向，並綁定通行條件
    e.g. 需要「撬鎖工具」才能進入廢棄工廠
    """

    __tablename__ = "node_connections"

    id = Column(Integer, primary_key=True, index=True)
    from_node_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=False)
    is_bidirectional = Column(Boolean, default=True)  # False = 單向通行
    label = Column(String(100))                        # "北方小道", "生鏽的鐵門"

    # 通行條件（JSON 字串），格式與 StoryCondition 相同
    # e.g. '[{"type":"item_check","key":"lockpick","op":">=","value":1}]'
    condition_json = Column(Text, nullable=True)

    from_node = relationship(
        "MapNode",
        foreign_keys=[from_node_id],
        back_populates="connections_from",
    )
    to_node = relationship(
        "MapNode",
        foreign_keys=[to_node_id],
        back_populates="connections_to",
    )


class SceneEvent(Base):
    """
    場景中可觸發的事件
    event_type: random_combat / fixed_loot / npc_encounter / story_trigger
    trigger_chance: 進入場景後的觸發機率 (0.0 ~ 1.0)，fixed 事件填 1.0
    """

    __tablename__ = "scene_events"

    id = Column(Integer, primary_key=True, index=True)
    map_node_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=False)
    name = Column(String(100))
    event_type = Column(String(30), nullable=False)  # random_combat/fixed_loot/npc_encounter/story_trigger
    trigger_chance = Column(Float, default=0.3)
    is_repeatable = Column(Boolean, default=True)    # 是否可重複觸發
    cooldown_turns = Column(Integer, default=0)      # 觸發冷卻（以回合計）

    # 若 event_type = story_trigger，連到哪個劇情節點
    linked_story_node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=True)

    # 若 event_type = random_combat，使用哪個戰鬥模板（預留，之後實作）
    combat_template_id = Column(Integer, nullable=True)

    # 若 event_type = fixed_loot，掉落物品 JSON
    # e.g. '[{"item_key":"med_kit","qty":1,"chance":0.8}]'
    loot_json = Column(Text, nullable=True)

    map_node = relationship("MapNode", back_populates="events")
