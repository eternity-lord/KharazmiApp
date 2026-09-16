from sqlalchemy.orm import Session
import models
from models import User, SessionLocal, engine

# اتصال به دیتابیس
models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

def create_super_admin():
    # چک کنیم اگر مدیر هست نسازیم
    exists = db.query(User).filter(User.username == "admin").first()
    if exists:
        print("⚠️ مدیر قبلاً وجود دارد.")
        return

    admin = User(
        username="09120000000", # شماره موبایل مدیر (نام کاربری)
        password="123",         # رمز عبور مدیر
        full_name="مدیر کل سیستم",
        role="admin"
    )
    db.add(admin)
    db.commit()
    print("✅ مدیر با موفقیت ساخته شد!")
    print("User: 09120000000 | Pass: 123")

if __name__ == "__main__":
    create_super_admin()
