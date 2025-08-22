from sqlalchemy.orm import Session
from . import models, schemas

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        email=user.email,
        comment=user.comment  # 👈 ahora guarda el comentario
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
