from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./game.db"
# 如果將來換 Postgres，可以改成 "postgresql://user:password@postgresserver/db"

# connect_args={"check_same_thread": False} 是 SQLite 專用的設定（用來支援 FastAPI 的多執行緒）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class 給所有的 ORM model 繼承
Base = declarative_base()

# FastAPI 的 Dependency 用於取得資料庫連線
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
