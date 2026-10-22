import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ...repositories.category_repository import (
    DuplicateCategoryError,
    fetch_categories,
    insert_category,
    update_category,
)
from ..dependencies import APP_ONLY, APP_OR_BOT, get_conn
from ..schemas import CategoryIn, CategoryOut

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut], dependencies=[APP_OR_BOT])
def get_categories(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    return [CategoryOut.from_model(category) for category in fetch_categories(conn)]


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=201,
    dependencies=[APP_ONLY],
)
def post_category(body: CategoryIn, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    try:
        category = insert_category(conn, body.to_model())
    except DuplicateCategoryError:
        raise HTTPException(
            status_code=422, detail="Category name or emoji already exists"
        ) from None
    return CategoryOut.from_model(category)


@router.patch(
    "/categories/{category_id}", response_model=CategoryOut, dependencies=[APP_ONLY]
)
def patch_category(
    category_id: int,
    body: CategoryIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        category = update_category(conn, category_id, body.to_model())
    except DuplicateCategoryError:
        raise HTTPException(
            status_code=422, detail="Category name or emoji already exists"
        ) from None

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut.from_model(category)
