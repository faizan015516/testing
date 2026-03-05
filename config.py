import os

class Config:
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "uploads")

    # Azure SQL Database
    AZURE_SQL_CONNECTION_STRING = os.environ.get("AZURE_SQL_CONNECTION_STRING")

    # App settings
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    @classmethod
    def validate(cls):
        missing = []
        if not cls.AZURE_STORAGE_CONNECTION_STRING:
            missing.append("AZURE_STORAGE_CONNECTION_STRING")
        if not cls.AZURE_SQL_CONNECTION_STRING:
            missing.append("AZURE_SQL_CONNECTION_STRING")
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
