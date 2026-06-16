from api.common.code import ResponseCode
from api.common.error import CustomException
from api.common.password import generate_salt, hash_password, verify_password
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

    async def register(self, username: str, email: str, password: str) -> User:
        """注册新用户

        Args:
            username: 用户名
            email: 邮箱
            password: 明文密码

        Returns:
            创建的用户实例

        Raises:
            CustomException: 用户名或邮箱已存在时抛出
        """
        # 检查用户名是否已存在
        existing = await db.session.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            raise CustomException(
                message=ResponseCode.USER_ALREADY_EXISTS.message,
                code=ResponseCode.USER_ALREADY_EXISTS.code,
                status_code=409,
            )

        # 检查邮箱是否已存在
        existing = await db.session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise CustomException(
                message=ResponseCode.USER_ALREADY_EXISTS.message,
                code=ResponseCode.USER_ALREADY_EXISTS.code,
                status_code=409,
            )

        # 生成随机 salt 并计算密码哈希
        salt = generate_salt()
        password_hash = hash_password(password, salt)

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
        )
        db.session.add(user)
        await db.session.flush()
        return user

    async def login(self, username: str, password: str) -> User:
        """验证用户凭据并返回用户实例

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            用户实例

        Raises:
            CustomException: 用户名不存在或密码错误时抛出
        """
        result = await db.session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            raise CustomException(
                message=ResponseCode.INVALID_CREDENTIALS.message,
                code=ResponseCode.INVALID_CREDENTIALS.code,
                status_code=401,
            )
        if not verify_password(password, user.salt, user.password_hash):
            raise CustomException(
                message=ResponseCode.INVALID_CREDENTIALS.message,
                code=ResponseCode.INVALID_CREDENTIALS.code,
                status_code=401,
            )
        return user
