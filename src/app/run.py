import uvicorn

from app.core.config import settings
from app.main import app

uvicorn.run(app, host=settings.run.host, port=settings.run.port)
