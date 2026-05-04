from app.repositories.base import BaseRepository
from app.models.user import User
from typing import Optional

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.model.find_one(self.model.username == username)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.find_one(self.model.email == email)

user_repo = UserRepository()
