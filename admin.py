from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

import config
from config import SQLADMIN_HASHED_PASSWORD
from enums.user_role import UserRole
from utils.utils import create_access_token, decode_token, verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == "admin" and verify_password(password, SQLADMIN_HASHED_PASSWORD):
            token = create_access_token(
                {
                    "sub": UserRole.ADMIN.name,
                }
            )

            request.session.update({"token": token})
            return True
        else:
            return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False

        payload = decode_token(token)
        if not payload:
            return False

        return True


authentication_backend = AdminAuth(secret_key=config.JWT_SECRET_KEY)
