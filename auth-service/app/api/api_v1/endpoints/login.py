# app/api/api_v1/endpoints/login.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.crud.crud_user   import get_user_by_email
from app.core.security    import verify_password, create_access_token
from app.db.session       import get_db
from app.core.rate_limit  import limiter
from app.schemas.user     import Token

router = APIRouter()

@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 password‑grant token endpoint",
)
@limiter.limit("5/minute")
def login_for_access_token(
    request: Request,  # ← must be here for slowapi to work
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Expects form fields:
      grant_type="password", username=<email>, password=<password>
    Returns JSON: { access_token: str, token_type: "bearer" }
    """
    # Authenticate
    db_user = get_user_by_email(db, form_data.username)
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue JWT
    token = create_access_token(subject=db_user.id)
    return {"access_token": token, "token_type": "bearer"}
