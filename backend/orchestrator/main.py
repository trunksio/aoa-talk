from fastapi import FastAPI

app = FastAPI(title="AOA Orchestrator Service")

@app.get("/")
def root():
    return {"message": "AOA Orchestrator running"}
