from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import engine, Base, get_db

# 載入 models 以便 Base.metadata.create_all 可以發現它們
from app.models import system, character
from app.core.combat_engine import manager as combat_manager

# 建立所有資料表 (僅限開發環境可以直接這樣做)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="末日超能力生存遊戲 API", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to Doomsday RPG API!"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # 簡單測試資料庫連線
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Database is connected"}
    except Exception as e:
        return {"status": "Database error", "details": str(e)}

# --- WebSocket 戰鬥路由測試 ---

@app.post("/combat/start/{combat_id}")
async def start_mock_combat(combat_id: str):
    """(測試用) 建立一場給定 ID 的戰鬥實例，放進記憶體中開始 Tick"""
    player_mock = {"name": "玩家", "current_hp": 100, "max_hp": 100, "current_mp": 50, "max_mp": 50, "intellect": 8, "agility": 5}
    enemy_mock = {"name": "變異感染者", "current_hp": 150, "max_hp": 150, "strength": 12, "technique": 4}
    
    combat = combat_manager.get_or_create_combat(combat_id, player_mock, enemy_mock)
    return {"status": "started", "combat_id": combat_id}

@app.websocket("/ws/combat/{combat_id}")
async def websocket_combat_endpoint(websocket: WebSocket, combat_id: str):
    """前端透過 WebSocket 連上來操作這場戰鬥"""
    combat = combat_manager.get_combat(combat_id)
    if not combat:
        await websocket.close(code=1008, reason="戰鬥不存在或已結束")
        return
        
    await combat.connect(websocket)
    import time
    try:
        while True:
            # 接收前端的行為 (施放技能)
            data = await websocket.receive_json()
            if data and data.get("action"):
                combat.process_player_action(data, time.time())
    except WebSocketDisconnect:
        combat.disconnect(websocket)

