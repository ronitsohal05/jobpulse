from __future__ import annotations

from fastapi import APIRouter

from app.api.resumes import router as resumes_router
from app.api.jobs import router as jobs_router
from app.api.search import router as search_router
from app.api.applications import router as applications_router
from app.api.admin_crawler import router as crawler_router
from app.api.topics import router as topics_router
from app.api.events import router as events_router


api_router = APIRouter()
api_router.include_router(resumes_router)
api_router.include_router(jobs_router)
api_router.include_router(applications_router)
api_router.include_router(search_router)
api_router.include_router(crawler_router)
api_router.include_router(topics_router)
api_router.include_router(events_router)

