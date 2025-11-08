# backend-fastapi/src/auth.py

import os
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
from typing import Annotated

# --- КОНФИГУРАЦИЯ ---
# Ключ должен совпадать с SECRET_KEY/JWT_SECRET_KEY, используемым в Django
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-fallback-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def get_current_user(
    Authorization: Annotated[str, Header()] = None
) -> int:
    """
    FastAPI Dependency: Проверяет JWT access токен, выданный Django,
    и возвращает ID пользователя (user_id).
    """
    if not Authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует заголовок авторизации",
        )

    # Проверяем схему
    if not Authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная схема авторизации (ожидается Bearer)"
        )

    # Извлекаем сам токен
    token = Authorization.split(" ", 1)[1].strip()

    try:
        # Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Извлекаем user_id (SimpleJWT кладёт его именно так)
        user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
        token_type = payload.get("token_type")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="В токене отсутствует user_id"
            )

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Требуется access-токен, получен: {token_type}"
            )

        return int(user_id)

    except JWTError as e:
        print(f"JWT Validation Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный, просроченный или поврежденный токен"
        )