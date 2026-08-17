from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import predict, history, stats

app = FastAPI(title="FraudLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(history.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok"}