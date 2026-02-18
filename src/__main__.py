"""Entry point: python -m src"""
import uvicorn

from src.transport.app import create_app

app = create_app()
uvicorn.run(app, host="0.0.0.0", port=8000)
