from fastapi import APIRouter, Depends, HTTPException, status, Response
from backend.models.user import User
from backend.models.admin import Admin
from backend.schemas.api_schemas import LoginRequest, SignupRequest, TokenResponse
from backend.utils.security import verify_password, get_password_hash, create_access_token
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup")
async def signup(payload: SignupRequest):
    # Check if user already exists
    existing_user = await User.find_one(User.email == payload.email)
    if existing_user:
        return api_response(
            success=False,
            message="User with this email already exists",
            status_code=400
        )
    
    # Create new user
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        phone=payload.phone,
        address=payload.address,
        status="active"
    )
    await user.insert()
    
    # Generate token
    token = create_access_token({"sub": str(user.id), "role": "user"})
    
    return api_response(
        success=True,
        message="Account created successfully",
        data={
            "token": token,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email
            }
        }
    )

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    # Try logging in as User first
    user = await User.find_one(User.email == payload.email)
    if user and verify_password(payload.password, user.password_hash):
        if user.status != "active":
            return api_response(
                success=False,
                message="Account has been blocked. Please contact support.",
                status_code=403
            )
            
        token = create_access_token({"sub": str(user.id), "role": "user"})
        # Set cookie for potential HTML client
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        
        return api_response(
            success=True,
            message="Login successful",
            data={
                "token": token,
                "role": "user",
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email
                }
            }
        )
        
    # Check if this is an Admin logging in via email field (fallback check)
    admin = await Admin.find_one(Admin.email == payload.email)
    if admin and verify_password(payload.password, admin.password_hash):
        if admin.status != "active":
            return api_response(
                success=False,
                message="Admin account is inactive",
                status_code=403
            )
            
        token = create_access_token({"sub": str(admin.id), "role": "admin"})
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        
        return api_response(
            success=True,
            message="Admin login successful",
            data={
                "token": token,
                "role": "admin",
                "user": {
                    "id": str(admin.id),
                    "name": admin.username,
                    "email": admin.email
                }
            }
        )

    return api_response(
        success=False,
        message="Invalid email or password",
        status_code=401
    )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return api_response(
        success=True,
        message="Logout successful"
    )

@router.get("/profile")
async def profile(user: User = Depends(get_current_user)):
    return api_response(
        success=True,
        message="Profile retrieved successfully",
        data={
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "address": user.address
        }
    )
