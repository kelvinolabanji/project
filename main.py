from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth, utils
from deps import get_db, get_current_user
from database import engine

# ==========================
# CREATE APP
# ==========================
app = FastAPI(title="OnePortal Backend")

# ==========================
# CORS MIDDLEWARE
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with ["https://your-frontend.onrender.com"] when deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# DATABASE INIT
# ==========================
models.Base.metadata.create_all(bind=engine)

# ==========================
# DEPARTMENT ASSIGNMENT
# ==========================
DEPARTMENT_MAP = {
    "life insurance": "Life Insurance",
    "claims": "Claims",
    "investments": "Investments",
    "general": "Customer Service"
}

def assign_department(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    for key, dept in DEPARTMENT_MAP.items():
        if key in text:
            return dept
    return DEPARTMENT_MAP["general"]

# ==========================
# SIGNUP
# ==========================
@app.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
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

    except Exception as e:
        print("SIGNUP ERROR:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ==========================
# LOGIN
# ==========================
@app.post("/login")
def login(data: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.email == data.email).first()
        if not user or not auth.verify_password(data.password, user.password):
            raise HTTPException(status_code=400, detail="Invalid credentials")
        token = auth.create_token({"id": user.id, "role": user.role})
        utils.log_action(db, user.id, "User logged in")
        return {"token": token, "role": user.role}
    except Exception as e:
        print("LOGIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ==========================
# ADMIN ROUTES
# ==========================
@app.get("/admin/users", response_model=List[schemas.UserResponse])
def admin_view_users(page: int = 1, limit: int = 10, search: str = "", user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    query = db.query(models.User)
    if search:
        query = query.filter(models.User.name.ilike(f"%{search}%"))
    users = query.offset((page-1)*limit).limit(limit).all()
    return users

@app.put("/admin/users/{user_id}", response_model=schemas.UserResponse)
def admin_edit_user(user_id: int, update: schemas.UserUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in update.dict(exclude_unset=True).items():
        if field == "password":
            value = auth.hash_password(value)
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    utils.log_action(db, user["id"], f"Edited user {user_id}")
    return db_user

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    utils.log_action(db, user["id"], f"Deleted user {user_id}")
    return {"message": "User deleted"}

@app.get("/admin/analytics")
def admin_analytics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    total_users = db.query(models.User).count()
    total_customers = db.query(models.User).filter(models.User.role == "customer").count()
    total_admins = db.query(models.User).filter(models.User.role == "admin").count()
    return {"total_users": total_users, "customers": total_customers, "admins": total_admins}

@app.get("/admin/requests", response_model=List[schemas.RequestResponse])
def admin_view_requests(department: str = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    query = db.query(models.Request)
    if department:
        query = query.filter(models.Request.department == department)
    return query.all()

# ==========================
# CUSTOMER ROUTES
# ==========================
@app.put("/customer/profile", response_model=schemas.UserResponse)
def customer_update_profile(update: schemas.UserUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user["id"]).first()
    for field, value in update.dict(exclude_unset=True).items():
        if field == "password":
            value = auth.hash_password(value)
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    utils.log_action(db, user["id"], "Updated profile")
    return db_user

@app.post("/customer/requests", response_model=schemas.RequestResponse)
def create_request(req: schemas.RequestCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    department = assign_department(req.title, req.description or "")
    new_req = models.Request(
        title=req.title,
        description=req.description,
        department=department,
        user_id=user["id"]
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    utils.log_action(db, user["id"], f"Created request {new_req.id} directed to {department}")
    return new_req

@app.get("/customer/requests", response_model=List[schemas.RequestResponse])
def list_requests(user=Depends(get_current_user), db: Session = Depends(get_db)):
    requests = db.query(models.Request).filter(models.Request.user_id == user["id"]).all()
    return requests

# ==========================
# ACTIVITY LOGS
# ==========================
@app.get("/activity_logs", response_model=List[schemas.ActivityLogResponse])
def get_activity_logs(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        logs = db.query(models.ActivityLog).filter(models.ActivityLog.user_id == user["id"]).all()
    else:
        logs = db.query(models.ActivityLog).all()
    return logs

