def log_action(db, user_id: int, action: str):
    from models import ActivityLog
    log = ActivityLog(user_id=user_id, action=action)
    db.add(log)
    db.commit()

def send_email(to_email: str, subject: str, content: str):
    print(f"Email to {to_email} - Subject: {subject}\n{content}")
