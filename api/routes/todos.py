from fastapi import APIRouter, HTTPException
from api.models import TodoCreate, TodoUpdate, TodoOut
from api.database import todos_collection
from bson import ObjectId

router = APIRouter(prefix="/todos", tags=["todos"])


def _doc_to_out(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    return doc


@router.post("/", response_model=TodoOut)
async def create_todo(todo: TodoCreate):
    doc = todo.model_dump()
    doc["done"] = False
    result = await todos_collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc


@router.get("/{user_id}", response_model=list[TodoOut])
async def get_todos(user_id: str):
    todos = []
    async for doc in todos_collection.find({"user_id": user_id}):
        todos.append(_doc_to_out(doc))
    return todos


@router.patch("/{todo_id}", response_model=TodoOut)
async def update_todo(todo_id: str, data: TodoUpdate):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    result = await todos_collection.find_one_and_update(
        {"_id": ObjectId(todo_id)},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Todo not found")
    return _doc_to_out(result)


@router.delete("/{todo_id}")
async def delete_todo(todo_id: str):
    result = await todos_collection.delete_one({"_id": ObjectId(todo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Deleted"}
