"""
story.py — 劇情系統層
包含：劇情章節 / 劇情節點 / 玩家選項 / 觸發條件 / 結果效果 / 結局 / 玩家劇情狀態
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


class StoryArc(Base):
    """
    劇情弧線（章節 / 路線）
    每條結局路線對應一個 Arc，多個 StoryNode 組成一條 Arc
    e.g. Arc "真相之路", Arc "倖存者聯盟線", Arc "孤狼結局"
    """

    __tablename__ = "story_arcs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)   # "真相之路"
    description = Column(Text)                    # 這條路線的背景說明（GM 用）
    is_main_story = Column(Boolean, default=False) # 是否為主線

    nodes = relationship("StoryNode", back_populates="arc")
    ending = relationship("Ending", back_populates="arc", uselist=False)


class StoryNode(Base):
    """
    單一劇情節點（一段對話、事件描述，或選擇點）
    node_type:
        - dialogue   : NPC / 旁白 說話
        - narration  : 純旁白敘述
        - choice     : 玩家選擇點（下方有 StoryChoice）
        - battle_intro: 戰鬥前置文字（之後觸發 Combat）
        - ending     : 結局節點
    """

    __tablename__ = "story_nodes"

    id = Column(Integer, primary_key=True, index=True)
    arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=True)
    map_node_id = Column(Integer, ForeignKey("map_nodes.id"), nullable=True)  # 發生在哪個地點

    # 發言者（NPC 名稱 or "旁白" or 空=玩家視角）
    speaker = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)              # 正文文字
    node_type = Column(String(20), default="dialogue")  # dialogue/narration/choice/battle_intro/ending

    # 沒有選項時，自動跳轉的下一個節點
    auto_next_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=True)

    arc = relationship("StoryArc", back_populates="nodes")
    choices = relationship(
        "StoryChoice",
        back_populates="node",
        order_by="StoryChoice.order",
        foreign_keys="[StoryChoice.node_id]",
    )
    auto_next = relationship("StoryNode", remote_side=[id], foreign_keys=[auto_next_id])


class StoryChoice(Base):
    """
    玩家選項，掛在某個 StoryNode 下
    若條件不符合，選項可能隱藏（is_visible = False）或顯示但禁用
    """

    __tablename__ = "story_choices"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=False)
    next_node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=True)
    label = Column(String(200), nullable=False)  # 選項顯示文字
    order = Column(Integer, default=0)           # 排列順序
    hide_if_locked = Column(Boolean, default=False)  # 條件不符時是否隱藏（True）還是顯示為灰色（False）

    node = relationship(
        "StoryNode",
        foreign_keys=[node_id],
        back_populates="choices",
    )
    next_node = relationship(
        "StoryNode",
        foreign_keys=[next_node_id],
    )
    conditions = relationship("StoryCondition", back_populates="choice")
    effects = relationship("StoryEffect", back_populates="choice")


class StoryCondition(Base):
    """
    選項觸發條件
    condition_type:
        - stat_check     : 屬性門檻，e.g. strength >= 15
        - item_check     : 持有物品，e.g. has lockpick >= 1
        - flag_check     : 劇情旗標，e.g. rescued_npc_a == true
        - rep_check      : 派系聲望，e.g. faction_rep("survivors") >= 50
        - class_check    : 職業限定，e.g. class_id in [2,3]
        - talent_check   : 天賦限定
    """

    __tablename__ = "story_conditions"

    id = Column(Integer, primary_key=True, index=True)
    choice_id = Column(Integer, ForeignKey("story_choices.id"), nullable=False)
    condition_type = Column(String(30), nullable=False)
    # key: 屬性名、物品key、flag名、派系名等
    key = Column(String(100), nullable=False)
    # op: >=, <=, ==, !=, in
    op = Column(String(10), default=">=")
    # value: 數字或 JSON 字串（"true"/"false"，或 "[2,3]" for in）
    value = Column(String(100), nullable=False)
    fail_message = Column(String(200), nullable=True)  # 條件不符時的提示文字

    choice = relationship("StoryChoice", back_populates="conditions")


class StoryEffect(Base):
    """
    選擇後觸發的效果
    effect_type:
        - stat_change    : 改屬性/衍伸數值，e.g. hunger += 20 / hp -= 30
        - flag_set       : 設定劇情旗標，e.g. rescued_npc_a = true
        - item_give      : 給予物品，e.g. give med_kit x2
        - item_remove    : 移除物品
        - trigger_combat : 觸發戰鬥（帶入 combat_template_id）
        - teleport       : 傳送到地圖節點
        - ending_trigger : 觸發結局
        - rep_change     : 改變派系聲望
    """

    __tablename__ = "story_effects"

    id = Column(Integer, primary_key=True, index=True)
    choice_id = Column(Integer, ForeignKey("story_choices.id"), nullable=False)
    effect_type = Column(String(30), nullable=False)
    key = Column(String(100), nullable=False)   # 屬性名/物品key/flag名/派系名
    op = Column(String(10), default="=")        # =, +=, -=
    value = Column(String(100), nullable=False) # 數值或 JSON
    delay_turns = Column(Integer, default=0)    # 延遲幾回合後生效（0=立即）

    choice = relationship("StoryChoice", back_populates="effects")


class Ending(Base):
    """
    固定結局定義
    ending_type: good / bad / neutral / true / secret
    """

    __tablename__ = "endings"

    id = Column(Integer, primary_key=True, index=True)
    arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=False)
    title = Column(String(100), nullable=False)      # "真相大白・光明結局"
    description = Column(Text)                       # 結局劇情摘要
    ending_type = Column(String(20), default="neutral")  # good/bad/neutral/true/secret
    trigger_node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=False)

    arc = relationship("StoryArc", back_populates="ending")
    trigger_node = relationship("StoryNode")


class PlayerStoryState(Base):
    """
    玩家劇情進度（獨立表，取代原本 Character.story_flags JSON 欄位）
    每個玩家角色對應一筆記錄
    flags_json: 動態劇情旗標，e.g. '{"rescued_npc_a":true,"boss1_killed":false}'
    """

    __tablename__ = "player_story_states"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, unique=True)
    current_node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=True)
    current_arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=True)
    flags_json = Column(Text, default="{}")  # 劇情旗標 key-value，用 json.loads/dumps 操作
    visited_nodes_json = Column(Text, default="[]")  # 已訪問過的 node id 列表

    character = relationship("Character", back_populates="story_state")
    current_node = relationship("StoryNode", foreign_keys=[current_node_id])
    current_arc = relationship("StoryArc", foreign_keys=[current_arc_id])
