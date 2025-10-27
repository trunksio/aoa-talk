from fastapi import FastAPI

app = FastAPI(title="AOA Planner Service")

@app.get("/")
def root():
    return {"message": "AOA Planner running"}
