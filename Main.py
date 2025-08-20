# main.py
import os, datetime, re
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from passlib.context import CryptContext
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
import jwt

app = FastAPI(title="ClearRead Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = os.getenv("JWT_SECRET", "change-this-secret")
ADMIN_HASH = os.getenv("ADMIN_PASS_HASH", None)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["clearread"]
settings_col = db["settings"]

class TermsRequest(BaseModel):
    text: str

class SettingsModel(BaseModel):
    startup_name: str
    slogan_hi: str
    slogan_en: str
    email: str
    phone: str
    whatsapp: str

class LoginModel(BaseModel):
    password: str

def create_token():
    exp = int((datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp())
    payload = {"role": "admin", "iat": int(datetime.datetime.utcnow().timestamp()), "exp": exp}
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verify_token(token: str) -> bool:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        return data.get("role") == "admin"
    except Exception:
        return False

@app.get("/settings")
def get_settings():
    doc = settings_col.find_one({"_id": "app_settings"})
    if not doc:
        doc = {
            "_id": "app_settings",
            "startup_name": "SamajhLo - Made in India",
            "slogan_hi": "शर्तें अब आसान – भारत में बना 🇮🇳",
            "slogan_en": "Terms Made Simple – Made in India 🇮🇳",
            "email": "jha689393@gmail.com",
            "phone": "8822876295",
            "whatsapp": "8822876295",
            "updated_at": datetime.datetime.utcnow()
        }
        settings_col.insert_one(doc)
    doc.pop("_id", None)
    return doc

@app.post("/admin/login")
def admin_login(body: LoginModel):
    if not ADMIN_HASH:
        raise HTTPException(status_code=500, detail="ADMIN_PASS_HASH not set on server.")
    if not pwd.verify(body.password, ADMIN_HASH):
        raise HTTPException(status_code=401, detail="Bad password")
    token = create_token()
    return {"token": token}

@app.post("/admin/settings")
def update_settings(new: SettingsModel, authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid token")
    doc = new.dict()
    doc["_id"] = "app_settings"
    doc["updated_at"] = datetime.datetime.utcnow()
    settings_col.replace_one({"_id": "app_settings"}, doc, upsert=True)
    return {"ok": True}

@app.post("/summarize")
def summarize(request: TermsRequest):
    text = request.text or ""
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    keywords = ["data", "consent", "collect", "share", "advert", "retain", "refund", "delete", "account", "payment"]
    points = [s.strip() for s in sentences if any(k in s.lower() for k in keywords)]
    if not points:
        points = sentences[:5]
    return {"summary": points}
