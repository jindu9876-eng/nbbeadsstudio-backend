import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database Configuration (PostgreSQL)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "nbbeadsstudio")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "YOUR_POSTGRES_PASSWORD")

    # Legacy MongoDB fallback settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/neeru1")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "neeru1")
    
    @property
    def POSTGRES_URL_ASYNC(self) -> str:
        from urllib.parse import quote_plus
        pwd = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def POSTGRES_URL_SYNC(self) -> str:
        from urllib.parse import quote_plus
        pwd = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def POSTGRES_SERVER_URL_ASYNC(self) -> str:
        from urllib.parse import quote_plus
        pwd = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/postgres"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretjwtkey12345!")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS Configuration (comma-separated origins or * for all)
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # Static files and uploads
    STATIC_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_FOLDER: str = os.getenv("CLOUDINARY_FOLDER", "NB BEADS STUDIO_ecommerce")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
