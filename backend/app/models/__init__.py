"""
models/__init__.py
統一 import 所有 ORM models，確保 Base.metadata.create_all() 能發現所有 Table
"""

from app.models.character import Character, PlayerCustomSkill  # noqa: F401
from app.models.story import (  # noqa: F401
    Ending,
    PlayerStoryState,
    StoryArc,
    StoryChoice,
    StoryCondition,
    StoryEffect,
    StoryNode,
)
from app.models.system import (  # noqa: F401
    ClassInfo,
    ClassLevelBonus,
    SystemSkillTemplate,
    Talent,
)
from app.models.world import MapNode, NodeConnection, SceneEvent  # noqa: F401
