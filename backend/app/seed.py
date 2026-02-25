"""
seed.py — 範例種子資料
展示各 Table 的實際資料格式，可直接執行插入 DB

執行方式（在 backend/ 目錄下）：
    python -m app.seed
"""

import json

from app.database import SessionLocal, engine
from app.database import Base  # Base 在 database.py，不在 models/__init__.py
from app.models import (  # 觸發所有 Table 建立（必須在 Base 之後 import 才能讓 metadata 完整）
    Character,
    ClassInfo,
    ClassLevelBonus,
    Ending,
    MapNode,
    NodeConnection,
    PlayerCustomSkill,
    PlayerStoryState,
    SceneEvent,
    StoryArc,
    StoryChoice,
    StoryCondition,
    StoryEffect,
    StoryNode,
    SystemSkillTemplate,
    Talent,
)


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── 1. 職業 ─────────────────────────────────────────────
        cls_psychic = ClassInfo(
            name="念動力者",
            description="以精神力操控物質的異能者，擅長遠端攻擊與偵測。",
            can_promote_to_json=json.dumps([2]),   # 可轉職到 id=2（見下方）
            base_stat_bonus_json=json.dumps({"intellect": 5, "perception": 3}),
        )
        cls_berserker = ClassInfo(
            name="狂戰士",
            description="用憤怒驅動異能的近戰特化者，受傷越重越強。",
            can_promote_to_json=json.dumps([]),
            base_stat_bonus_json=json.dumps({"strength": 6, "agility": 2}),
        )
        cls_phantom = ClassInfo(
            name="幽影使者",
            description="念動力者的轉職，可操縱幻覺與空間扭曲。",
            can_promote_to_json=json.dumps([]),
            base_stat_bonus_json=json.dumps({"intellect": 8, "charisma": 4}),
        )
        db.add_all([cls_psychic, cls_berserker, cls_phantom])
        db.flush()  # 取得 id 後繼續

        # 職業等級加成
        db.add_all([
            ClassLevelBonus(
                class_id=cls_psychic.id,
                level=5,
                stat_bonus_json=json.dumps({"max_mp": 20, "intellect": 2}),
            ),
            ClassLevelBonus(
                class_id=cls_psychic.id,
                level=10,
                stat_bonus_json=json.dumps({"max_mp": 30, "intellect": 3, "max_hp": 20}),
            ),
            ClassLevelBonus(
                class_id=cls_berserker.id,
                level=5,
                stat_bonus_json=json.dumps({"max_hp": 40, "strength": 3}),
            ),
        ])

        # ── 2. 天賦 ─────────────────────────────────────────────
        talent_iron = Talent(
            name="鐵骨",
            description="身體異常強韌，最大HP永久+30。",
            effect_type="buff_stat",
            effect_json=json.dumps({"stat": "max_hp", "value": 30}),
            condition_json=None,  # 永久被動
        )
        talent_berserk = Talent(
            name="濒死狂乱",
            description="HP 低於 30% 時，力量 +8。",
            effect_type="unique_passive",
            effect_json=json.dumps({"stat": "strength", "value": 8}),
            condition_json=json.dumps({"trigger": "on_low_hp", "threshold": 0.3}),
        )
        db.add_all([talent_iron, talent_berserk])
        db.flush()

        # ── 3. 系統技能範本 ──────────────────────────────────────
        skill_telekinesis = SystemSkillTemplate(
            base_name="念動衝擊",
            description="以精神力壓縮空氣，猛烈衝擊敵人。",
            skill_type="active",
            base_damage=25,
            cooldown_sec=4.0,
            cost_mp=12,
            scaling_stat="intellect",
            scaling_ratio=1.5,
            is_aoe=False,
            range_type="single",
        )
        skill_aoe_blast = SystemSkillTemplate(
            base_name="念動爆破",
            description="向四周釋放爆炸性念力，傷害範圍內所有敵人。",
            skill_type="active",
            base_damage=15,
            cooldown_sec=8.0,
            cost_mp=25,
            scaling_stat="intellect",
            scaling_ratio=1.2,
            is_aoe=True,
            range_type="aoe",
        )
        skill_dodge = SystemSkillTemplate(
            base_name="急速閃避",
            description="瞬間加速閃開攻擊，成功時回復部分MP。",
            skill_type="reaction",
            base_damage=0,
            cooldown_sec=6.0,
            cost_mp=8,
            scaling_stat="agility",
            scaling_ratio=0.0,
            is_aoe=False,
            range_type="self",
        )
        db.add_all([skill_telekinesis, skill_aoe_blast, skill_dodge])
        db.flush()

        # 綁定 ClassLevelBonus 解鎖技能
        db.add(ClassLevelBonus(
            class_id=cls_psychic.id,
            level=3,
            stat_bonus_json=json.dumps({"max_mp": 10}),
            unlock_skill_id=skill_aoe_blast.id,
        ))

        # ── 4. 地圖節點（多層級）────────────────────────────────
        region_city = MapNode(
            name="靜默之城",
            description="曾是繁榮的大都市，末日後幾乎無人生還，廢墟中偶有異能者出沒。",
            node_type="region",
            danger_level=3,
            is_safe_zone=False,
            image_key="bg_ruined_city",
        )
        db.add(region_city)
        db.flush()

        area_industrial = MapNode(
            name="工業區廢墟",
            description="龐大的廠房已傾頹，空氣中飄散著不明物質。",
            node_type="area",
            danger_level=4,
            is_safe_zone=False,
            image_key="bg_industrial",
            parent_id=region_city.id,
        )
        area_residential = MapNode(
            name="住宅區殘骸",
            description="公寓大樓半塌，仍有少數倖存者躲藏其中。",
            node_type="area",
            danger_level=2,
            is_safe_zone=False,
            image_key="bg_residential",
            parent_id=region_city.id,
        )
        db.add_all([area_industrial, area_residential])
        db.flush()

        building_factory = MapNode(
            name="廢棄工廠",
            description="巨大的金屬機具已停止運轉，冷卻槽中有異能能量殘留。",
            node_type="building",
            danger_level=5,
            is_safe_zone=False,
            image_key="bg_factory",
            parent_id=area_industrial.id,
        )
        building_shelter = MapNode(
            name="地下避難所",
            description="倖存者自建的臨時庇護所，守衛會盤問陌生人。",
            node_type="building",
            danger_level=1,
            is_safe_zone=True,
            image_key="bg_shelter",
            parent_id=area_residential.id,
        )
        db.add_all([building_factory, building_shelter])
        db.flush()

        room_core = MapNode(
            name="工廠核心艙",
            description="一個密封的房間，中央有一個散發詭異光芒的裝置——末日的源頭或許就在這裡。",
            node_type="room",
            danger_level=5,
            is_safe_zone=False,
            image_key="bg_core_room",
            parent_id=building_factory.id,
        )
        db.add(room_core)
        db.flush()

        # ── 5. 節點連接 ──────────────────────────────────────────
        conn_to_industrial = NodeConnection(
            from_node_id=region_city.id,
            to_node_id=area_industrial.id,
            is_bidirectional=True,
            label="往工業區",
            condition_json=None,
        )
        conn_to_residential = NodeConnection(
            from_node_id=region_city.id,
            to_node_id=area_residential.id,
            is_bidirectional=True,
            label="往住宅區",
            condition_json=None,
        )
        conn_factory_locked = NodeConnection(
            from_node_id=area_industrial.id,
            to_node_id=building_factory.id,
            is_bidirectional=False,          # 進去容易，出來需從另一側離開
            label="工廠生鏽大門（需撬鎖）",
            condition_json=json.dumps([
                {"type": "item_check", "key": "lockpick", "op": ">=", "value": 1}
            ]),
        )
        conn_core_hidden = NodeConnection(
            from_node_id=building_factory.id,
            to_node_id=room_core.id,
            is_bidirectional=True,
            label="隱藏通道（需感知 >= 15）",
            condition_json=json.dumps([
                {"type": "stat_check", "key": "perception", "op": ">=", "value": 15}
            ]),
        )
        db.add_all([conn_to_industrial, conn_to_residential, conn_factory_locked, conn_core_hidden])
        db.flush()

        # ── 6. 場景事件 ──────────────────────────────────────────
        event_patrol = SceneEvent(
            map_node_id=area_industrial.id,
            name="異能獵人巡邏",
            event_type="random_combat",
            trigger_chance=0.4,
            is_repeatable=True,
            cooldown_turns=3,
        )
        event_supply = SceneEvent(
            map_node_id=building_shelter.id,
            name="補給箱",
            event_type="fixed_loot",
            trigger_chance=1.0,
            is_repeatable=False,
            loot_json=json.dumps([
                {"item_key": "med_kit", "qty": 2, "chance": 0.8},
                {"item_key": "ration_pack", "qty": 3, "chance": 1.0},
            ]),
        )
        db.add_all([event_patrol, event_supply])
        db.flush()

        # ── 7. 劇情 Arc ──────────────────────────────────────────
        arc_truth = StoryArc(
            title="真相之路",
            description="主線劇情，玩家追查末日起因，最終揭露核心裝置的秘密。",
            is_main_story=True,
        )
        arc_survivors = StoryArc(
            title="倖存者聯盟線",
            description="選擇加入倖存者組織，以集體力量對抗威脅，但需要犧牲部分自由。",
            is_main_story=False,
        )
        db.add_all([arc_truth, arc_survivors])
        db.flush()

        # ── 8. 劇情節點 ──────────────────────────────────────────
        node_intro = StoryNode(
            arc_id=arc_truth.id,
            map_node_id=region_city.id,
            speaker="旁白",
            content="城市的輪廓在灰塵中隱沒。你站在廢墟的邊緣，感受著從體內涌動的異能——那是末日之後，你唯一的武器。",
            node_type="narration",
        )
        db.add(node_intro)
        db.flush()

        node_choice1 = StoryNode(
            arc_id=arc_truth.id,
            map_node_id=region_city.id,
            speaker="旁白",
            content="眼前有兩條路。工業區的廢墟深處藏著某種異能訊號，而住宅區的避難所裡似乎有人在呼叫求援。",
            node_type="choice",
            auto_next_id=None,
        )
        db.add(node_choice1)
        db.flush()

        node_investigate = StoryNode(
            arc_id=arc_truth.id,
            map_node_id=area_industrial.id,
            speaker="旁白",
            content="你跟著訊號深入工業區。訊號越來越強烈，你感覺到腦中一陣刺痛——像是有什麼東西在試圖與你連結。",
            node_type="narration",
        )
        node_rescue = StoryNode(
            arc_id=arc_survivors.id,
            map_node_id=area_residential.id,
            speaker="倖存者・林",
            content="謝天謝地你來了！我們的人被困在三樓，下面有異能獵人在巡邏……你有辦法幫我們嗎？",
            node_type="dialogue",
        )
        node_intro.auto_next_id = None  # 序章：手動推進到 choice1
        db.add_all([node_investigate, node_rescue])
        db.flush()

        # node_intro -> node_choice1（自動推進）
        node_intro.auto_next_id = node_choice1.id

        # ── 9. 玩家選項 ──────────────────────────────────────────
        choice_go_industrial = StoryChoice(
            node_id=node_choice1.id,
            next_node_id=node_investigate.id,
            label="跟著異能訊號，前往工業區廢墟。",
            order=0,
            hide_if_locked=False,
        )
        choice_go_shelter = StoryChoice(
            node_id=node_choice1.id,
            next_node_id=node_rescue.id,
            label="響應求援訊號，前往住宅區避難所。",
            order=1,
            hide_if_locked=False,
        )
        # 隱藏選項：需要高感知才能察覺到第三條路
        choice_hidden_core = StoryChoice(
            node_id=node_choice1.id,
            next_node_id=node_investigate.id,  # 暫時指向同地點，之後可換成 room_core 的節點
            label="【你感知到城市中心有一股壓倒性的異能……】直接前往核心。",
            order=2,
            hide_if_locked=True,   # 條件不符時完全隱藏
        )
        db.add_all([choice_go_industrial, choice_go_shelter, choice_hidden_core])
        db.flush()

        # ── 10. 觸發條件 ─────────────────────────────────────────
        # choice_hidden_core 需要 perception >= 18
        cond_high_perception = StoryCondition(
            choice_id=choice_hidden_core.id,
            condition_type="stat_check",
            key="perception",
            op=">=",
            value="18",
            fail_message="你感覺到某種微弱的波動，但無法確定來源。",
        )
        db.add(cond_high_perception)

        # ── 11. 觸發效果 ─────────────────────────────────────────
        # 選擇前往工業區：飢渴+10，並設定劇情 flag
        effect_hunger = StoryEffect(
            choice_id=choice_go_industrial.id,
            effect_type="stat_change",
            key="hunger",
            op="+=",
            value="10",
        )
        effect_flag_industrial = StoryEffect(
            choice_id=choice_go_industrial.id,
            effect_type="flag_set",
            key="visited_industrial",
            op="=",
            value="true",
        )
        # 選擇救援：魅力+1（倖存者對你好感上升），設定 flag
        effect_charisma_rescue = StoryEffect(
            choice_id=choice_go_shelter.id,
            effect_type="stat_change",
            key="charisma",
            op="+=",
            value="1",
        )
        effect_flag_rescue = StoryEffect(
            choice_id=choice_go_shelter.id,
            effect_type="flag_set",
            key="joined_survivors",
            op="=",
            value="true",
        )
        db.add_all([effect_hunger, effect_flag_industrial, effect_charisma_rescue, effect_flag_rescue])

        # ── 12. 結局 ─────────────────────────────────────────────
        node_ending_truth = StoryNode(
            arc_id=arc_truth.id,
            map_node_id=room_core.id,
            speaker="旁白",
            content="核心裝置在你指尖崩解。真相終於攤在陽光下——末日並非天災，而是人類自己種下的種子。你選擇了什麼，決定了這顆種子最後長出什麼。",
            node_type="ending",
        )
        db.add(node_ending_truth)
        db.flush()

        ending_truth = Ending(
            arc_id=arc_truth.id,
            title="真相大白・光明結局",
            description="玩家揭露了末日的真正原因，並以異能摧毀了核心裝置，為世界帶來一線希望。",
            ending_type="good",
            trigger_node_id=node_ending_truth.id,
        )
        db.add(ending_truth)

        # ── 13. 角色範例 ─────────────────────────────────────────
        char_player = Character(
            user_id=1,
            name="玩家一號",
            class_id=cls_psychic.id,
            current_node_id=region_city.id,
            level=1,
            exp=0,
            strength=5,
            agility=7,
            intellect=12,
            perception=10,
            charisma=6,
            technique=5,
            max_hp=100,
            current_hp=100,
            max_mp=80,
            current_mp=80,
            hunger=0,
            thirst=0,
        )
        char_player.talents = [talent_iron]
        db.add(char_player)
        db.flush()

        # 自定義技能
        custom_skill = PlayerCustomSkill(
            character_id=char_player.id,
            template_id=skill_telekinesis.id,
            custom_name="漆黑念刃",
            custom_description="從意識深處凝聚的黑色刀刃，切割現實本身。",
            vfx_color="#1a004d",
            vfx_style="dark_blade",
        )
        db.add(custom_skill)

        # 玩家劇情狀態（獨立表）
        story_state = PlayerStoryState(
            character_id=char_player.id,
            current_node_id=node_intro.id,
            current_arc_id=arc_truth.id,
            flags_json=json.dumps({"game_started": True}),
            visited_nodes_json=json.dumps([node_intro.id]),
        )
        db.add(story_state)

        db.commit()
        print("[OK] Seed 完成：所有範例資料已寫入 DB")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Seed 失敗：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
