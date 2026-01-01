from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.schemas import UserProfileUpdate, AddressCreate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return user

@router.put("/me")
def update_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return UserService.update_profile(db, user, data)

@router.post("/address")
def add_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return UserService.add_address(db, user.user_id, data)
