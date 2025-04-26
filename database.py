from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
import ssl
from contextlib import contextmanager

# ===== Configuration =====
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))  # Render free tier recommendation
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "3"))

# ===== SSL Configuration =====
def create_ssl_context():
    ssl_context = ssl.create_default_context()
    if os.getenv("DB_SSL_MODE", "require") == "verify-full":
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(cafile=os.getenv("DB_SSL_ROOT_CERT"))
    return ssl_context

# ===== Engine Configuration =====
engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_pre_ping=True,  # Check connections before use
    pool_recycle=300,  # Recycle connections after 5 minutes
    connect_args={
        "connect_timeout": 5,
        "ssl": create_ssl_context() if DATABASE_URL.startswith("postgresql") else None
    },
    echo=bool(os.getenv("SQL_DEBUG", ""))  # Enable for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ===== Models =====
class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Security features
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime(timezone=True))

# ===== Database Initialization =====
def init_db():
    Base.metadata.create_all(bind=engine)

# ===== Session Management =====
@contextmanager
def get_db():
    """Secure database session generator with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

# ===== Health Check =====
def check_db_health():
    """Verify database connectivity"""
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return True
    except Exception as e:
        return False

# Initialize on import if in production
if os.getenv("ENVIRONMENT") == "production":
    init_db()
