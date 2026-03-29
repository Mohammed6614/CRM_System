import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-legendary-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///' + str(BASE_DIR / 'crm_system.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
