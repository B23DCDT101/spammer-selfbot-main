from fastapi import FastAPI
from api.routes.todos import router

app = FastAPI(title="Todo API")
app.include_router(router)
