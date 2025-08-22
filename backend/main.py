import os
import httpx
import asyncio
from datetime import datetime, date
from typing import Optional, List
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pathlib
from pydantic import BaseModel, EmailStr
import sqlite3, os
from typing import Optional
from pydantic import BaseModel, EmailStr
import bleach, sqlite3, os
from fastapi import HTTPException

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime,
    DECIMAL, Text, func, text
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
import bleach
from dotenv import load_dotenv
load_dotenv()


Base = declarative_base()


# ---------------------------------------------------------------------
# 2) Modelos
# ---------------------------------------------------------------------
class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    room_type = Column(String(100))
    capacity = Column(Integer)
    price_per_night = Column(DECIMAL(10, 2))
    status = Column(String(20), default="Disponible")

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(30))
    country = Column(String(100))
    city = Column(String(100))
    checkin_date = Column(Date)
    checkout_date = Column(Date)
    guests = Column(Integer)
    room_type = Column(String(100))
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100))
    email = Column(String(100))
    message = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)

class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True)
    city = Column(String(100))
    temperature = Column(DECIMAL(5, 2))
    description = Column(String(200))
    humidity = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class CleanedReservation(Base):
    __tablename__ = "cleaned_reservations"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(30))
    country = Column(String(100))
    city = Column(String(100))
    checkin_date = Column(Date)
    checkout_date = Column(Date)
    guests = Column(Integer)
    room_type = Column(String(100))
    comments = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)
    data_quality_score = Column(DECIMAL(3, 2))



# Conexión única leyendo .env (SQLite por defecto)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./hotel_reservas.db")

# Para SQLite hay que pasar check_same_thread=False
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(DB_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Crear tablas (ya con los modelos definidos)
Base.metadata.create_all(bind=engine)

# (Opcional) Semilla mínima si no hay reservas
def _seed_if_empty():
    try:
        with SessionLocal() as db:
            if db.query(Reservation).count() == 0:
                db.add(Reservation(
                    first_name="María", last_name="González", email="maria@example.com",
                    phone="8888-1234", country="Costa Rica", city="San José",
                    checkin_date=date(2025, 9, 1), checkout_date=date(2025, 9, 4),
                    guests=2, room_type="Suite Vista al Mar", comments="Demo"
                ))
                db.commit()
                print("📝 Semilla insertada")
    except Exception as e:
        print(f"⚠️ Seed error: {e}")

_seed_if_empty()



# Crea las tablas si no existen (solo si hay conexión)
if engine:
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas de BD verificadas/creadas")
    except Exception as e:
        print(f"⚠️ Error creando tablas: {e}")
        engine = None
        SessionLocal = None

# ---------------------------------------------------------------------
# 3) Esquemas Pydantic
# ---------------------------------------------------------------------
class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int

class ReservationCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    country: Optional[str] = None
    city: Optional[str] = None
    checkin_date: date
    checkout_date: date
    guests: int
    room_type: str
    comments: Optional[str] = None

    @validator('first_name', 'last_name')
    def sanitize_names(cls, v):
        return bleach.clean(v.strip()) if v else v
    
    @validator('comments')
    def sanitize_comments(cls, v):
        return bleach.clean(v.strip()) if v else v
    
    @validator('guests')
    def validate_guests(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Número de huéspedes debe estar entre 1 y 10')
        return v

class ContactCreate(BaseModel):
    full_name: str
    email: EmailStr
    message: str
    
    @validator('full_name')
    def sanitize_name(cls, v):
        return bleach.clean(v.strip())
    
    @validator('message')
    def sanitize_message(cls, v):
        return bleach.clean(v.strip())

# ---------------------------------------------------------------------
# 4) App FastAPI
# ---------------------------------------------------------------------
app = FastAPI(title="Hotel Costa Bella API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ubicación de la carpeta frontend
BACKEND_DIR = pathlib.Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

# Servir archivos estáticos (CSS, JS, imágenes)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

# Cuando entres a "/", devolverá tu index.html
@app.get("/")
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))



# Dependencia para obtener sesión de BD
def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configuración de variables de entorno
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "demo_key")  # Obtener de variables de entorno
security = HTTPBearer()

# Función para obtener datos del clima (API externa)
async def get_weather_data(city: str = "San José") -> Optional['WeatherResponse']:
    """Consume API de OpenWeatherMap para obtener datos del clima"""
    
    # Datos demo específicos para ciudades de Costa Rica
    costa_rica_weather = {
        "San José": {"temp": 24, "desc": "parcialmente nublado", "humidity": 75},
        "Alajuela": {"temp": 27, "desc": "soleado", "humidity": 68},
        "Cartago": {"temp": 20, "desc": "fresco y nublado", "humidity": 82},
        "Heredia": {"temp": 22, "desc": "templado", "humidity": 78},
        "Liberia": {"temp": 32, "desc": "caluroso y seco", "humidity": 55},
        "Puntarenas": {"temp": 29, "desc": "húmedo y cálido", "humidity": 85},
        "Puerto Limón": {"temp": 28, "desc": "tropical húmedo", "humidity": 88}
    }
    
    try:
        if WEATHER_API_KEY == "demo_key":
            # Usar datos específicos para Costa Rica
            print(f"🌡️ Generando datos de clima demo para {city}")
            
            # Buscar datos específicos de la ciudad o usar San José por defecto
            city_data = costa_rica_weather.get(city, costa_rica_weather["San José"])
            
            # Agregar variación pequeña basada en la hora actual
            import random
            temp_variation = random.uniform(-2, 2)
            humidity_variation = random.randint(-5, 5)
            
            return WeatherResponse(
                city=city,
                temperature=city_data["temp"] + temp_variation,
                description=city_data["desc"],
                humidity=max(30, min(95, city_data["humidity"] + humidity_variation))
            )
        
        # Si tenemos API key real, usar OpenWeatherMap
        # Mapear nombres de ciudades para mejor compatibilidad con API
        city_mapping = {
            "San José": "San Jose, CR",
            "Alajuela": "Alajuela, CR", 
            "Cartago": "Cartago, CR",
            "Heredia": "Heredia, CR",
            "Liberia": "Liberia, CR",
            "Puntarenas": "Puntarenas, CR",
            "Puerto Limón": "Limon, CR"
        }
        
        api_city = city_mapping.get(city, f"{city}, Costa Rica")
        
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": api_city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "es"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return WeatherResponse(
                    city=city,  # Usar el nombre original
                    temperature=data["main"]["temp"],
                    description=data["weather"][0]["description"],
                    humidity=data["main"]["humidity"]
                )
            else:
                print(f"⚠️ Error API OpenWeatherMap: {response.status_code}")
                # Fallback a datos demo
                city_data = costa_rica_weather.get(city, costa_rica_weather["San José"])
                return WeatherResponse(
                    city=city,
                    temperature=city_data["temp"],
                    description=city_data["desc"],
                    humidity=city_data["humidity"]
                )
    except Exception as e:
        print(f"Error obteniendo datos del clima: {e}")
        # Fallback a datos demo en caso de error
        city_data = costa_rica_weather.get(city, costa_rica_weather["San José"])
        return WeatherResponse(
            city=city,
            temperature=city_data["temp"],
            description=city_data["desc"],
            humidity=city_data["humidity"]
        )
    
    return None

# ----------------------------- Endpoints -----------------------------
@app.get("/")
def root():
    return {"message": "Hotel Costa Bella API"}

@app.get("/rooms")
def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()

@app.post("/reservations")
def create_reservation(payload: ReservationCreate, db: Session = Depends(get_db)):
    db_res = Reservation(**payload.dict())
    db.add(db_res)
    db.commit()
    db.refresh(db_res)
    return {"ok": True, "reservation_id": db_res.id}

@app.get("/reservations")
def list_reservations():
    """Lista todas las reservas"""
    try:
        if not engine or not SessionLocal:
            # Si no hay conexión de BD, retornar datos demo
            return [
                {
                    "id": 1,
                    "first_name": "María",
                    "last_name": "González",
                    "email": "maria@example.com",
                    "room_type": "Suite Vista al Mar",
                    "checkin_date": "2025-08-15",
                    "checkout_date": "2025-08-18",
                    "guests": 2,
                    "created_at": "2025-08-10T10:00:00"
                },
                {
                    "id": 2,
                    "first_name": "Carlos",
                    "last_name": "Rodríguez",
                    "email": "carlos@example.com",
                    "room_type": "Villa Privada",
                    "checkin_date": "2025-08-20",
                    "checkout_date": "2025-08-23",
                    "guests": 4,
                    "created_at": "2025-08-09T15:30:00"
                },
                {
                    "id": 3,
                    "first_name": "Ana",
                    "last_name": "López",
                    "email": "ana@example.com",
                    "room_type": "Habitación Deluxe",
                    "checkin_date": "2025-08-25",
                    "checkout_date": "2025-08-27",
                    "guests": 1,
                    "created_at": "2025-08-08T09:15:00"
                }
            ]
            
        db = SessionLocal()
        try:
            return db.query(Reservation).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Error en reservations endpoint: {e}")
        # En caso de error, retornar datos demo
        return [
            {
                "id": 1,
                "first_name": "Demo",
                "last_name": "Reservation",
                "room_type": "Suite Vista al Mar"
            }
        ]

@app.post("/contact")
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    db_msg = ContactMessage(**payload.dict())
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return {"ok": True, "message_id": db_msg.id}

# Nuevos endpoints para API externa y pipeline
@app.get("/api/weather/{city}", response_model=WeatherResponse)
async def get_weather(city: str):
    """Obtiene datos del clima y opcionalmente los almacena en BD"""
    print(f"🌤️ Solicitando clima para: {city}")
    weather_data = await get_weather_data(city)
    
    if not weather_data:
        # Retornar datos demo si falla
        weather_data = WeatherResponse(
            city=city,
            temperature=24.0,
            description="datos no disponibles",
            humidity=70
        )
    
    # Intentar guardar en base de datos si está disponible
    if engine and SessionLocal:
        try:
            db = SessionLocal()
            try:
                db_weather = WeatherData(
                    city=weather_data.city,
                    temperature=weather_data.temperature,
                    description=weather_data.description,
                    humidity=weather_data.humidity
                )
                db.add(db_weather)
                db.commit()
                print(f"✅ Datos del clima guardados en BD: {weather_data.city}")
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ No se pudieron guardar datos del clima: {e}")
    
    return weather_data

@app.get("/api/weather-history")
def get_weather_history():
    """Obtiene historial de datos del clima"""
    try:
        if not engine or not SessionLocal:
            # Retornar historial demo
            return [
                {
                    "id": 1,
                    "city": "San José",
                    "temperature": 24.5,
                    "description": "parcialmente nublado",
                    "humidity": 78,
                    "recorded_at": "2025-08-10T12:00:00"
                }
            ]
            
        db = SessionLocal()
        try:
            return db.query(WeatherData).order_by(WeatherData.recorded_at.desc()).limit(50).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Error en weather-history endpoint: {e}")
        return []

@app.get("/api/stats/reservations")
def get_reservation_stats():
    """Estadísticas de reservas para el dashboard"""
    try:
        # Verificar si tenemos conexión a la base de datos
        if not engine or not SessionLocal:
            print("⚠️ Sin conexión a BD, usando datos demo en stats")
            return {
                "total_reservations": 24,
                "monthly_reservations": 8,
                "most_popular_room": ["Suite Vista al Mar", 6]
            }
            
        # Intentar conectar a la base de datos
        db = SessionLocal()
        try:
            print("🔍 Consultando estadísticas reales desde MySQL...")
            total_reservations = db.query(func.count(Reservation.id)).scalar() or 0
            print(f"📊 Total reservas encontradas: {total_reservations}")
            
            # Para reservas mensuales, usar un filtro más simple
            try:
                recent_reservations = db.query(func.count(Reservation.id)).filter(
                    Reservation.created_at >= datetime.utcnow().replace(day=1)
                ).scalar() or 0
                print(f"📊 Reservas del mes: {recent_reservations}")
            except Exception as e:
                print(f"⚠️ Error calculando reservas mensuales: {e}")
                # Si falla, usar total/4 como estimado mensual
                recent_reservations = max(1, total_reservations // 4) if total_reservations > 0 else 0
            
            # Obtener la habitación más popular
            try:
                popular_room_query = db.query(
                    Reservation.room_type, 
                    func.count(Reservation.room_type).label('count')
                ).group_by(Reservation.room_type).order_by(
                    func.count(Reservation.room_type).desc()
                ).first()
                
                most_popular_room = None
                if popular_room_query:
                    most_popular_room = [popular_room_query[0], popular_room_query[1]]
                    print(f"📊 Habitación más popular: {most_popular_room}")
                else:
                    most_popular_room = ["Sin reservas", 0]
                    print("📊 No hay habitaciones populares aún")
            except Exception as e:
                print(f"⚠️ Error calculando habitación popular: {e}")
                most_popular_room = ["Suite Vista al Mar", 0]
            
            result = {
                "total_reservations": total_reservations,
                "monthly_reservations": recent_reservations,
                "most_popular_room": most_popular_room
            }
            print(f"✅ Estadísticas reales calculadas: {result}")
            return result
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error en stats endpoint: {e}")
        # Retornar datos por defecto en caso de error
        return {
            "total_reservations": 0,
            "monthly_reservations": 0,
            "most_popular_room": ["Error", 0]
        }

@app.get("/api/cleaned-reservations")
def get_cleaned_reservations():
    """Obtiene reservas procesadas por el pipeline"""
    try:
        if not engine or not SessionLocal:
            # Si no hay conexión de BD, retornar datos demo
            return [
                {
                    "id": 1,
                    "original_id": 1,
                    "first_name": "María",
                    "last_name": "González",
                    "room_type": "Suite Vista al Mar",
                    "data_quality_score": 0.95,
                    "processed_at": "2025-08-10T12:00:00"
                },
                {
                    "id": 2,
                    "original_id": 2,
                    "first_name": "Carlos",
                    "last_name": "Rodríguez",
                    "room_type": "Villa Privada",
                    "data_quality_score": 0.92,
                    "processed_at": "2025-08-10T11:30:00"
                }
            ]
            
        db = SessionLocal()
        try:
            return db.query(CleanedReservation).order_by(CleanedReservation.processed_at.desc()).limit(100).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Error en cleaned-reservations endpoint: {e}")
        # Si la tabla no existe o hay error, retornar lista con datos demo
        return [
            {
                "id": 1,
                "first_name": "Demo",
                "last_name": "User",
                "room_type": "Suite Vista al Mar",
                "data_quality_score": 0.98
            }
        ]

@app.get("/health")
def health_check():
    """Health check endpoint para verificar que la API funciona"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Hotel Costa Bella API is running"
    }

@app.get("/api/dashboard/test")
def dashboard_test():
    """Endpoint de prueba específico para el dashboard"""
    return {
        "dashboard_status": "working",
        "endpoints_available": [
            "/api/stats/reservations",
            "/api/cleaned-reservations", 
            "/api/weather-history",
            "/reservations"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

# --- SEGURIDAD: registro con sanitización (respuesta limpia) ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    comment: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    comment: Optional[str] = None

def _sqlite_path_from_url(url: str) -> str:
    if url.startswith("sqlite:////"):
        return url.replace("sqlite:////", "/")
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return url

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./hotel_reservas.db")
DB_PATH = _sqlite_path_from_url(DB_URL)

def ensure_users_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                comment TEXT
            );
        """)
        conn.commit()

@app.on_event("startup")
def _startup_create_users():
    ensure_users_table()

@app.post("/register", response_model=UserOut, tags=["security"])
def register(user: UserCreate):
    # permite <b>, <i>, <strong>, <em> y remueve todo lo demás (incl. <script>)
    allowed = ["b", "i", "strong", "em"]
    safe_comment = bleach.clean(user.comment or "", tags=allowed, attributes={}, strip=True)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, comment) VALUES (?, ?, ?)",
                (user.username.strip(), user.email, safe_comment),
            )
            user_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Usuario o email ya existe")

    # pa probarsh en el post --- error en el return 
    return {
        "id": user_id,
        "username": user.username.strip(),
        "email": user.email,
        "comment": safe_comment,
    }
