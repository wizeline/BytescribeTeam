from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from .core.config import settings
from .routers import beckrock


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# CORS (để gọi từ frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(beckrock.router)

# Adapter cho AWS Lambda (API Gateway / Function URL)
handler = Mangum(app)
