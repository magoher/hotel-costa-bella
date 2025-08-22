import os
import bleach
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, database, schemas

# 1. Manejo de secretos
load_dotenv()
DB_URL = os.getenv("DB_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "default_key")

app = FastAPI(title="Hotel Costa Bella - Secure API")

# Dependencia DB
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Sanitización de inputs
def sanitize_text(text: str) -> str:
    return bleach.clean(text, tags=[], attributes={}, strip=True)

# 3. Endpoint seguro
@app.post("/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    clean_comment = sanitize_text(user.comment or "")

    # Reemplazar el comment con el saneado
    user.comment = clean_comment

    db_user = crud.create_user(db=db, user=user)
    if not db_user:
        raise HTTPException(status_code=400, detail="Error al registrar usuario")
    return db_user

# 4. HTTPS → ejecutar con:
# uvicorn secure_app:app --host 0.0.0.0 --port 8000 \
#   --ssl-keyfile=./certs/privkey.pem \
#   --ssl-certfile=./certs/fullchain.pem
