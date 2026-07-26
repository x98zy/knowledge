import hashlib
import os
import tempfile
from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select

from common.code import ResponseCode
from common.const import USER_HAS_LOGIN_CACHE_KEY, USER_LOGIN_CACHE_KEY
from common.error import CustomException
from common.jwt import create_access_token
from common.password import generate_salt, hash_password, verify_password
from config.settings import settings
from extensions.ext_db import db
from extensions.ext_redis import redis_client
from extensions.ext_storage import storage
from models.document import UploadFile as UploadFileModel
from models.user import User


class UserService:
    """用户服务类"""

    @classmethod
    async def logout(cls, user_id: str):
        """用户退出登录

        Args:
            user_id: 用户 ID
        """
        await redis_client.delete(USER_LOGIN_CACHE_KEY.format(user_id=user_id))
        await redis_client.delete(USER_HAS_LOGIN_CACHE_KEY.format(user_id=user_id))

    @classmethod
    async def change_password(cls, user_id: str, old_password: str, new_password: str):
        """修改用户密码

        Args:
            user_id: 用户 ID
            old_password: 旧密码
            new_password: 新密码

        Raises:
            CustomException: 旧密码错误时抛出
        """
        query = select(User).where(User.id == user_id)
        result = await db.session.execute(query)
        user = result.scalars().first()
        if not user:
            raise CustomException(
                message=ResponseCode.USER_NOT_FOUND.message,
                code=ResponseCode.USER_NOT_FOUND.code,
                status_code=404,
            )
        if not verify_password(old_password, user.salt, user.password_hash):
            raise CustomException(
                message=ResponseCode.INVALID_PASSWORD.message,
                code=ResponseCode.INVALID_PASSWORD.code,
                status_code=401,
            )
        # 生成新的 salt 并计算新密码哈希
        new_salt = generate_salt()
        new_password_hash = hash_password(new_password, new_salt)
        user.salt = new_salt
        user.password_hash = new_password_hash
        await db.session.commit()

    @classmethod
    async def get_user_profile(cls, user_id: str) -> dict:
        """获取用户信息接口"""
        query = select(User).where(User.id == user_id)
        result = await db.session.execute(query)
        user = result.scalars().first()
        if not user:
            raise CustomException(
                message=ResponseCode.USER_NOT_FOUND.message,
                code=ResponseCode.USER_NOT_FOUND.code,
                status_code=404,
            )
        user_info = user.dict
        if user.avator_file_key:
            user_info["avator_url"] = storage.get_signed_url(user.avator_file_key)
        else:
            user_info["avator_url"] = None
        return user_info

    @classmethod
    async def upload_avator(cls, file: UploadFile, user_id: str):
        """上传用户头像

        Args:
            file: 上传的文件
            user_id: 用户 ID

        Returns:
            上传后的文件路径
        """
        # 上传文件到存储
        suffix = os.path.splitext(file.filename)[-1] if file.filename and "." in file.filename else ""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        try:
            # 2. 计算哈希
            query = select(User).where(User.id == user_id)
            current_user = await db.session.execute(query)
            current_user = current_user.scalars().first()

            file_hash = hashlib.sha256(content).hexdigest()

            # 3. 生成 OSS 文件 Key
            ext = suffix.lstrip(".") if suffix else ""
            file_key = f"uploads/{uuid4().hex}.{ext}" if ext else f"uploads/{uuid4().hex}"

            # 4. 上传到 OSS
            await storage.put_object(file_name=tmp_path, file_key=file_key)

            # 5. 写入数据库
            record = UploadFileModel(
                file_name=file.filename or file_key,
                file_hash=file_hash,
                file_key=file_key,
                file_size=len(content),
                ext=ext,
                created_by=current_user.username,
                updated_by=current_user.username,
            )
            current_user.avator_file_key = record.file_key
            db.session.add(record)
            await db.session.commit()

            return True
        finally:
            # 6. 清理临时文件
            os.unlink(tmp_path)

    @classmethod
    async def register(cls, username: str, email: str, password: str) -> User:
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

    @classmethod
    async def login(cls, username: str, password: str) -> User:
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
        user.last_login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        access_token = create_access_token(user.id)
        exist_token = await redis_client.get(USER_LOGIN_CACHE_KEY.format(user_id=user.id))
        print(4444444, exist_token)
        # 如果用户已经登录过设置一个缓存挤掉先前登录的用户
        if exist_token:
            await redis_client.set(
                USER_HAS_LOGIN_CACHE_KEY.format(user_id=user.id), 1, ex=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        # 设置新的登录缓存
        await redis_client.set(
            USER_LOGIN_CACHE_KEY.format(user_id=user.id), access_token, ex=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return access_token
