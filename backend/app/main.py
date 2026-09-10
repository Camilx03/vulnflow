from fastapi import FastAPI

app = FastAPI(
    title="VulnFlow API",
    description="API for the VulnFlow vulnerability management platform",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "vulnflow-api",
    }