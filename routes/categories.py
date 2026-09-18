from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from datetime import datetime
from backend.models.category import Category
from backend.schemas.api_schemas import CategoryCreate, CategoryUpdate
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_admin

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("")
async def get_categories(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    
    categories = await Category.find(query).sort("name").to_list()
    
    # Format categories with id str
    cats_list = []
    for c in categories:
        c_dict = c.model_dump()
        c_dict["id"] = str(c.id)
        cats_list.append(c_dict)
        
    return api_response(
        success=True,
        message="Categories fetched successfully",
        data=cats_list
    )

@router.post("", dependencies=[Depends(get_current_admin)])
async def create_category(payload: CategoryCreate):
    slug = payload.slug or payload.name.lower().replace(" ", "-").replace("&", "and")
    # Check if slug exists
    existing = await Category.find_one(Category.slug == slug)
    if existing:
        return api_response(
            success=False,
            message=f"Category with slug '{slug}' already exists",
            status_code=400
        )
        
    category = Category(
        name=payload.name,
        slug=slug,
        parent_id=payload.parent_id,
        image=payload.image,
        icon=payload.icon,
        status=payload.status
    )
    await category.insert()
    
    c_dict = category.model_dump()
    c_dict["id"] = str(category.id)
    
    return api_response(
        success=True,
        message="Category created successfully",
        data=c_dict,
        status_code=201
    )

@router.put("/{id}", dependencies=[Depends(get_current_admin)])
async def update_category(id: str, payload: CategoryUpdate):
    category = await Category.get(id)
    if not category:
        return api_response(
            success=False,
            message="Category not found",
            status_code=404
        )
        
    update_data = payload.model_dump(exclude_unset=True)
    
    # Validate slug if updated
    if "slug" in update_data and update_data["slug"] != category.slug:
        existing = await Category.find_one(Category.slug == update_data["slug"])
        if existing:
            return api_response(
                success=False,
                message=f"Category with slug '{update_data['slug']}' already exists",
                status_code=400
            )
            
    for key, value in update_data.items():
        setattr(category, key, value)
        
    category.updated_at = datetime.utcnow()
    await category.save()
    
    c_dict = category.model_dump()
    c_dict["id"] = str(category.id)
    
    return api_response(
        success=True,
        message="Category updated successfully",
        data=c_dict
    )

@router.delete("/{id}", dependencies=[Depends(get_current_admin)])
async def delete_category(id: str):
    category = await Category.get(id)
    if not category:
        return api_response(
            success=False,
            message="Category not found",
            status_code=404
        )
        
    await category.delete()
    return api_response(
        success=True,
        message="Category deleted successfully"
    )
