# FastAPI router for CRUD operations on users

from typing import Annotated

import psycopg2
from fastapi import APIRouter, Query, Depends, HTTPException, status

from database import get_db
from models.user import (
    create_user,
    get_all_users,
    get_user_by_id,
    update_user,
    set_user_active_status,
)
from schemas import UserCreate, UserResponse, UserUpdate, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["Users"])

DbDep = Annotated[psycopg2.extensions.connection, Depends(get_db)]


# Create
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def add_user(
    data: UserCreate, 
    db: DbDep, 
    admin=Depends(require_admin),
):
    # Create a new user.
    return create_user(db, data)

# Read
@router.get("/", response_model=list[UserResponse])
def list_users(db: DbDep, admin=Depends(require_admin),):
    # Return all users
    return get_all_users(db);


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbDep, admin=Depends(require_admin),):
    # Return a single user by ID
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

# Update
# TODO use get_current_user
@router.patch("/{user_id}", response_model=UserResponse)
def edit_user(user_id: int, data: UserUpdate, db: DbDep,):
    # (Partially) update a user.
    user = update_user(db, user_id, data)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

@router.patch("/{user_id}/role", response_model=UserResponse)
def edit_user_and_role(
    user_id: int, 
    data: UserRoleUpdate, 
    db: DbDep, 
    admin=Depends(require_admin),
):
    # (Partially) update a user.
    user = update_user(db, user_id, data)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

@router.patch("/{user_id}/active", response_model=UserResponse, status_code=status.HTTP_200_OK)
def set_user_active(
    user_id: int,
    is_active: bool = Query(...),
    force: bool = Query(default=False),
    db=Depends(get_db),
    admin=Depends(require_admin),
):
    try:
        user = set_user_active_status(db, user_id, is_active, force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    return user