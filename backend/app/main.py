from fastapi import FastAPI

app = FastAPI(
    title="Research-Flow",
    description="面向科研人员的全生命周期研究工作流管理平台",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
