"""从.env同步平台配置到Platform表（幂等迁移）

运行方式：
    cd backend
    C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.sync_platform_from_env
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.platform import Platform
from app.config import settings

# 平台配置映射（.env字段 -> Platform表字段）
PLATFORM_CONFIG_MAP = {
    "deepseek": {
        "name": "DeepSeek",
        "api_key": settings.DEEPSEEK_API_KEY,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "model": settings.DEEPSEEK_MODEL,
    },
    "glm": {
        "name": "GLM",
        "api_key": settings.GLM_API_KEY,
        "base_url": settings.GLM_BASE_URL,
        "model": settings.GLM_MODEL,
    },
    "minimax": {
        "name": "MiniMax",
        "api_key": settings.MINIMAX_API_KEY,
        "base_url": settings.MINIMAX_BASE_URL,
        "model": settings.MINIMAX_MODEL,
        "timeout": settings.MINIMAX_TIMEOUT,
    },
    "doubao": {
        "name": "豆包",
        "api_key": settings.DOUBAO_API_KEY,
        "base_url": settings.DOUBAO_BASE_URL,
        "model": settings.DOUBAO_MODEL or "doubao-seed-1.6",
    },
}


def run_migration():
    # 确保表存在
    Base.metadata.create_all(bind=engine, tables=[Platform.__table__])

    db = SessionLocal()
    try:
        synced = 0
        skipped = 0
        for code, config in PLATFORM_CONFIG_MAP.items():
            if not config["api_key"] or not config["base_url"]:
                print(f"  跳过 {code}: .env中未配置")
                skipped += 1
                continue

            existing = db.query(Platform).filter(Platform.code == code).first()
            if existing:
                print(f"  跳过 {code}: 已存在（id={existing.id}）")
                skipped += 1
                continue

            p = Platform(
                code=code,
                name=config["name"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                status=True,
                priority=100,
                timeout=config.get("timeout", 120),
                max_tokens=settings.MONITOR_MAX_TOKENS,
                temperature=settings.MONITOR_TEMPERATURE,
                platform_type="openai_compatible",
            )
            db.add(p)
            synced += 1
            print(f"  同步 {code}: {config['name']} ({config['model']})")

        db.commit()
        print(f"\n✅ 同步完成：新增 {synced} 个，跳过 {skipped} 个")
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始从.env同步平台配置到Platform表...")
    run_migration()
