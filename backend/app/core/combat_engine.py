# app/core/combat_engine.py
import asyncio
import time
from typing import Dict, Optional
from fastapi import WebSocket
from pydantic import BaseModel

class CombatState(BaseModel):
    """回傳給前端的戰鬥狀態封包"""
    combat_id: str
    player_hp: int
    player_max_hp: int
    player_mp: int
    player_max_mp: int
    enemy_hp: int
    enemy_max_hp: int
    player_cooldowns: Dict[str, float]  # {skill_id: ready_time}
    logs: list[str]
    is_active: bool
    # 新增機制
    enemy_action_state: str        # 'idle' or 'charging'
    enemy_action_progress: float   # 0.0 ~ 1.0 (給前端畫蓄力條)
    player_dodge_status: bool      # 玩家是否處於無敵狀態

class ActiveCombat:
    """管理單一戰鬥實例 (State Machine)"""
    def __init__(self, combat_id: str, player_data: dict, enemy_data: dict):
        self.combat_id = combat_id
        
        # 初始數值 (從 DB 讀出後轉成 dict 放記憶體)
        self.player = player_data
        self.enemy = enemy_data
        
        # 追蹤連線的 WebSocket
        self.connections: list[WebSocket] = []
        
        # 冷卻與效果追蹤
        self.player_cooldowns: Dict[str, float] = {}
        self.enemy_cooldowns: Dict[str, float] = {}
        
        # 新增戰鬥機制狀態
        self.enemy_state = "idle" # 'idle', 'charging'
        self.enemy_charge_start_time = 0.0
        self.enemy_charge_duration = 1.5 # 敵人蓄力 1.5 秒
        
        self.player_invulnerable_until = 0.0 # 無敵幀結束時間
        
        self.is_active = True
        self.combat_logs: list[str] = [f"戰鬥開始！遭遇了 {self.enemy.get('name', '敵人')}！"]
        self.task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        # 剛連線先送一次初始狀態
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast_state(self):
        """將當前記憶體中的血量與 CD 廣播給所有在此戰鬥中的網頁"""
        if not self.connections:
            return
            
        current_time = time.time()
        # 計算蓄力進度
        progress = 0.0
        if self.enemy_state == "charging" and self.enemy_charge_duration > 0:
            progress = (current_time - self.enemy_charge_start_time) / self.enemy_charge_duration
            progress = min(1.0, progress)
            
        state = CombatState(
            combat_id=self.combat_id,
            player_hp=self.player["current_hp"],
            player_max_hp=self.player["max_hp"],
            player_mp=self.player["current_mp"],
            player_max_mp=self.player["max_mp"],
            enemy_hp=self.enemy["current_hp"],
            enemy_max_hp=self.enemy["max_hp"],
            player_cooldowns=self.player_cooldowns,
            logs=self.combat_logs[-5:], # 只傳送最近 5 條 LOG
            is_active=self.is_active,
            enemy_action_state=self.enemy_state,
            enemy_action_progress=progress,
            player_dodge_status=(current_time < self.player_invulnerable_until)
        )
        
        for connection in self.connections:
            try:
                await connection.send_json(state.dict())
            except Exception:
                pass

    async def game_loop(self):
        """背景即時運算迴圈 (Tick)"""
        while self.is_active:
            current_time = time.time()
            
            # 1. 處理敵人 AI (蓄力與攻擊判定)
            if self.enemy_state == "idle":
                # 每 4 秒發起一次攻擊準備
                if current_time >= self.enemy_cooldowns.get("auto_attack", 0):
                    self.enemy_state = "charging"
                    self.enemy_charge_start_time = current_time
                    self.combat_logs.append(f"敵人正在蓄力準備攻擊！")
            
            elif self.enemy_state == "charging":
                # 檢查是否蓄力完成
                if current_time >= self.enemy_charge_start_time + self.enemy_charge_duration:
                    self.enemy_state = "idle"
                    self.enemy_cooldowns["auto_attack"] = current_time + 4.0 # 下一次攻擊在 4 秒後
                    
                    # 傷害與閃避判定
                    if current_time < self.player_invulnerable_until:
                        # 玩家無敵幀中，閃避成功！
                        self.combat_logs.append("【閃避成功】你躲開了致命的一擊！ MP +10")
                        self.player["current_mp"] = min(self.player["max_mp"], self.player["current_mp"] + 10)
                    else:
                        damage = max(1, self.enemy.get("strength", 5) - self.player.get("agility", 5) // 2)
                        self.player["current_hp"] -= damage
                        self.combat_logs.append(f"敵人狠狠地砸了下來，對你造成 {damage} 點傷害！")
            
            # 2. 檢查生死
            self.check_win_condition()
            
            # 3. 廣播狀態
            await self.broadcast_state()
            
            # 每 0.2 秒 Tick 一次 (5 FPS 網頁足夠了，降低伺服器負擔)
            await asyncio.sleep(0.2)
            
        # 當迴圈被 is_active = False 終止時，補送最後一次狀態給前端更新死亡畫面
        await self.broadcast_state()

    def process_player_action(self, action_data: dict, current_time: float):
        """處理前端傳來的指令 (施放技能/閃避)"""
        if not self.is_active:
            return
            
        action_type = action_data.get("action")
        
        if action_type == "dodge":
            # 閃避技能 CD
            if current_time < self.player_cooldowns.get("dodge", 0):
                self.combat_logs.append("閃避還在冷卻中！")
                return
            
            # 給予 0.5 秒無敵幀，冷卻 2.5 秒
            self.player_invulnerable_until = current_time + 0.5
            self.player_cooldowns["dodge"] = current_time + 2.5
            self.combat_logs.append("你進行了翻滾閃避！(無敵 0.5 秒)")
            
        elif action_type == "cast_skill":
            skill_id = str(action_data.get("skill_id")) # dictionary key convert
            # 這裡應該去 DB 撈 SystemSkillTemplate
            # 簡化示範：火球術 (ID 1), CD 5秒, 消耗 15 MP, 傷害 20
            mock_skill = {"id": 1, "base_damage": 20, "cooldown_sec": 5.0, "cost_mp": 15}
            
            # 檢查 CD (時間戳是否大於目前的 time)
            if current_time < self.player_cooldowns.get(skill_id, 0):
                self.combat_logs.append(f"技能還在冷卻中！")
                return

            # 檢查 MP
            if self.player["current_mp"] < mock_skill["cost_mp"]:
                self.combat_logs.append(f"MP 不足！")
                return

            # 執行技能
            self.player["current_mp"] -= mock_skill["cost_mp"]
            self.player_cooldowns[skill_id] = current_time + mock_skill["cooldown_sec"]
            
            # 計算傷害 (引進 mechanics 運算)
            from app.models.mechanics import calculate_damage
            damage = calculate_damage(mock_skill["base_damage"], 1.0, self.player, self.enemy)
            
            self.enemy["current_hp"] -= damage
            self.combat_logs.append(f"你使用了技能，造成 {damage} 點傷害！")
            
        self.check_win_condition()

    def check_win_condition(self):
        if self.enemy["current_hp"] <= 0:
            self.enemy["current_hp"] = 0
            self.is_active = False
            self.enemy_state = "idle"
            self.combat_logs.append("你贏得了這場戰鬥！")
        elif self.player["current_hp"] <= 0:
            self.player["current_hp"] = 0
            self.is_active = False
            self.enemy_state = "idle"
            self.combat_logs.append("你被擊倒了...")


class CombatManager:
    """管理 FastAPI 所有的活躍戰鬥"""
    def __init__(self):
        self.active_combats: Dict[str, ActiveCombat] = {}

    def get_or_create_combat(self, combat_id: str, player: dict, enemy: dict) -> ActiveCombat:
        if combat_id not in self.active_combats:
            combat = ActiveCombat(combat_id, player, enemy)
            # 啟動背景迴圈
            combat.task = asyncio.create_task(combat.game_loop())
            self.active_combats[combat_id] = combat
        return self.active_combats[combat_id]
        
    def get_combat(self, combat_id: str) -> Optional[ActiveCombat]:
        return self.active_combats.get(combat_id)

    def remove_combat(self, combat_id: str):
        combat = self.active_combats.get(combat_id)
        if combat:
            combat.is_active = False
            if combat.task:
               combat.task.cancel()
            del self.active_combats[combat_id]

# Singleton 實例供路由使用
manager = CombatManager()
