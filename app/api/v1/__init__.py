"""/api/v1 路由聚合（单一入口，§1.4）。

契约先行（§4.8）：`stub_*` 是未实现接口的 501 骨架，让 `openapi.json` 提前可用、
前端能并行开工。P1 实现某个接口时：把对应函数从 stub 文件删掉 → 新建真实模块 →
把新模块挪到 `stub_*` **之前**注册（同路径先注册者生效）。
"""

from fastapi import APIRouter

from app.api.v1 import auth, permissions, roles, stub_admin, stub_app, stub_files

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["认证 C"])
api_router.include_router(permissions.router, tags=["角色与权限 B"])
api_router.include_router(roles.router, tags=["角色与权限 B"])

# 契约先行的 501 骨架 —— P1 会逐个掏空，最终整块删除
api_router.include_router(stub_app.router, tags=["A 客户端业务 · 骨架"])
api_router.include_router(stub_admin.router, tags=["B 后台录入 · 骨架"])
api_router.include_router(stub_files.router, tags=["C 文件通道 · 骨架"])
