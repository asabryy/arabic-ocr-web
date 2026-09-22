from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_stripe_customer_id(db: Session, customer_id: str) -> User | None:
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def set_stripe_customer_id(db: Session, user: User, customer_id: str) -> User:
    user.stripe_customer_id = customer_id
    db.commit()
    db.refresh(user)
    return user
