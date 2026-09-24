"""/api/v1 路由聚合（单一入口，§1.4）。

契约先行：后续模块可以先只出返回 501 的骨架路由，让 openapi.json 提前可用（§5.8）。
"""

from fastapi import APIRouter

from app.api.v1 import auth, permissions, roles

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["认证 C"])
api_router.include_router(permissions.router, tags=["角色与权限 B"])
api_router.include_router(roles.router, tags=["角色与权限 B"])
