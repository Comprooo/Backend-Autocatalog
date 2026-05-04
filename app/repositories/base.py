from typing import TypeVar, Generic, List, Optional
from beanie import Document, PydanticObjectId
from pydantic import BaseModel

T = TypeVar("T", bound=Document)

class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]):
        self.model = model

    async def get(self, id: PydanticObjectId) -> Optional[T]:
        return await self.model.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        return await self.model.find_all().skip(skip).limit(limit).to_list()

    async def create(self, obj_in: BaseModel | dict) -> T:
        obj_data = obj_in.model_dump() if isinstance(obj_in, BaseModel) else obj_in
        db_obj = self.model(**obj_data)
        await db_obj.insert()
        return db_obj

    async def update(self, db_obj: T, obj_in: BaseModel | dict) -> T:
        obj_data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, BaseModel) else obj_in
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        await db_obj.save()
        return db_obj

    async def delete(self, id: PydanticObjectId) -> bool:
        obj = await self.get(id)
        if obj:
            await obj.delete()
            return True
        return False
