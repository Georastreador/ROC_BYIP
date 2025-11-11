from sqlalchemy.orm import Session
from sqlalchemy import text

def log(db: Session, action: str, detail: str = "", plan_id: int | None = None, actor: str = "analyst"):
    db.execute(text("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER, action TEXT, detail TEXT, actor TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
    db.execute(text("INSERT INTO audit_logs (plan_id, action, detail, actor) VALUES (:pid,:a,:d,:actor)"),
               {"pid": plan_id, "a": action, "d": detail, "actor": actor})
    db.commit()
