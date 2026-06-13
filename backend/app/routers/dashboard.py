from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.schemas.order import DashboardPage

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/borradores", response_model=DashboardPage)
def get_borradores(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)


@router.get("/aprobados", response_model=DashboardPage)
def get_aprobados(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)


@router.get("/enviados", response_model=DashboardPage)
def get_enviados(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)


@router.get("/confirmados", response_model=DashboardPage)
def get_confirmados(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)


@router.get("/alertas", response_model=DashboardPage)
def get_alertas(_=Depends(get_current_user)):
    return DashboardPage(items=[], total=0, page=1, size=50)
