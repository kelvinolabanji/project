from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

import models, schemas, auth, utils
from database import engine, SessionLocal
from deps import get_db, get_current_user

# Initialize FastAPI
app = FastAPI(title="OnePortal Backend")

# Allow frontend
FRONTEND_URL = os.environ.get("FRONTEND_URL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables in the DB if they don't exist
models.Base.metadata.create_all(bind=engine)

# ===== SIGNUP =====
@app.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=auth.hash_password(user.password),
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    utils.send_email(new_user.email, "Verify your account", "Click this link to verify!")
    utils.log_action(db, new_user.id, "User signed up")
    return {"message": "User created, verification email sent"}

