from fastapi import FastAPI
from routes import app as routes_app

app = FastAPI(title="DenialNet™", version="0.1.0")
app.include_router(routes_app)

@app.get("/")
def root():
    return {
        "name": "DenialNet™",
        "tagline": "The intelligence layer every claim system plugs into.",
        "version": "0.1.0",
        "docs": "/docs"
    }
