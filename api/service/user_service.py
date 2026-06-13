from api.extensions.ext_db import db
from api.models.user import User
from sqlalchemy import select


class UserService:
    """用户服务类"""

    async def get_user_list(self) -> list[User]:
        """获取用户列表"""
        query = select(User).order_by(User.id.desc())
        result = await db.session.execute(query)
        return result.scalars().all()
