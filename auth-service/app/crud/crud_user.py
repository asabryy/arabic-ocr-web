
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Retrieve a user record by email address.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Retrieve a user record by its primary key ID.
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Create a new user, hashing their password before storage.
    """
    hashed = hash_password(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        name=user_in.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_google_user(db: Session, email: str, name: str) -> User:
    """
    Create a user authenticated via Google OAuth (no password).
    """
    user = User(email=email, hashed_password=None, name=name, email_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """
    Update fields on a user record.
    """
    if user_in.name is not None:
        user.name = user_in.name

    db.commit()
    db.refresh(user)
    return user
