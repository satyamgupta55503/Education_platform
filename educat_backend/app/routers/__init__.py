"""EduCat AI — Router registry"""
from fastapi import APIRouter

from app.routers.auth import router as _auth
from app.routers.chat import router as _chat
from app.routers.users import router as _users
from app.routers.content import router as _content
from app.routers.subscriptions import router as _subs
from app.routers.school import router as _school
from app.routers._remaining import (
    router as _admin,
    teacher_router_export as _teacher,
    webhooks_router as _webhooks,
)

class _Routers:
    auth          = _auth
    chat          = _chat
    users         = _users
    content       = _content
    subscriptions = _subs
    admin         = _admin
    teacher       = _teacher
    webhooks      = _webhooks
    school        = _school

# Re-export for easy import
auth          = _auth
chat          = _chat
users         = _users
content       = _content
subscriptions = _subs
admin         = _admin
teacher       = _teacher
webhooks      = _webhooks
school        = _school
