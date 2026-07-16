from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.organisations import Organisation
from app.models.org_user import OrgUser
from app.schemas.auth import RegisterSchema, LoginSchema
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/register")
async def register(data: RegisterSchema):
    async with AsyncSessionLocal() as session:
        async with session.begin():

            # Check if email already exists
            result = await session.execute(
                select(User).where(User.email == data.email)
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")

            # Upsert organisation
            org_stmt = pg_insert(Organisation).values(
                name=data.org_name
            ).on_conflict_do_nothing().returning(Organisation.id)
            org_result = await session.execute(org_stmt)
            org_id = org_result.scalar_one_or_none()

            # If org already existed, fetch its id
            if org_id is None:
                org_result = await session.execute(
                    select(Organisation).where(Organisation.name == data.org_name)
                )
                org_id = org_result.scalar_one().id

            # Create user
            user = User(
                name=data.name,
                email=data.email,
                password_hash=hash_password(data.password)
            )
            session.add(user)
            await session.flush()  # gets user.id without committing

            # Link user to org
            org_user = OrgUser(
                user_id=user.id,
                org_id=org_id,
                role="admin"
            )
            session.add(org_user)

    return {"message": "Account created successfully"}


@router.post("/login")
async def login(data: LoginSchema):
    async with AsyncSessionLocal() as session:

        # Find user by email
        result = await session.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Get org_id from org_users
        org_result = await session.execute(
            select(OrgUser).where(OrgUser.user_id == user.id)
        )
        org_user = org_result.scalar_one_or_none()

        if not org_user:
            raise HTTPException(status_code=400, detail="User not linked to any organisation")

        # Create JWT token
        token = create_access_token({
            "user_id": user.id,
            "org_id": org_user.org_id
        })

        return {
            "access_token": token,
            "token_type": "bearer"
        }