from app import app
from ai.password_model import load_models
from database.database import init_db

init_db()
load_models()
