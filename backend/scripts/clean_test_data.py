"""清理测试数据脚本
删除测试用户及其关联数据，用于上线前清理。
使用方法：python scripts/clean_test_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.models.article import ArticleDraft
from app.models.monitor import MonitorRecord

TEST_USERNAMES = ["test_doctor", "test_doctor2", "test"]

def clean():
    db = SessionLocal()
    try:
        test_users = db.query(User).filter(User.username.in_(TEST_USERNAMES)).all()
        if not test_users:
            print("未找到测试用户，无需清理")
            return

        for user in test_users:
            print(f"清理用户: {user.username} (id={user.id})")
            # 删除关联数据
            db.query(MonitorRecord).filter(
                MonitorRecord.semantic_id.in_(
                    db.query(Semantic.id).filter(Semantic.user_id == user.id)
                )
            ).delete(synchronize_session=False)
            db.query(ArticleDraft).filter(ArticleDraft.user_id == user.id).delete()
            db.query(Semantic).filter(Semantic.user_id == user.id).delete()
            db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()

        db.commit()
        print(f"已清理 {len(test_users)} 个测试用户及其关联数据")
    except Exception as e:
        db.rollback()
        print(f"清理失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("确认清理测试数据？(yes/no): ")
    if confirm.lower() == "yes":
        clean()
    else:
        print("已取消")
