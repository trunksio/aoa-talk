from fastapi import FastAPI

app = FastAPI(title="AOA Registry Service")

@app.get("/")
def root():
    return {"message": "AOA Registry running"}
