from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from routes.admin_html import ADMIN_HTML

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/admin", response_class=HTMLResponse)
def admin_page():
    return ADMIN_HTML
