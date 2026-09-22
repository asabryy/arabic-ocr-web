from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # None for OAuth users
    name = Column(String(255), nullable=True)
    email_verified = Column(Boolean, default=False)
    # Account tier: "free" | "pro". Limits per plan are enforced in doc-manager.
    plan = Column(String(16), nullable=False, server_default="free", default="free")
    # Stripe linkage. plan stays the authoritative read path for quota enforcement
    # (doc-manager reads users.plan directly); these three are what the webhook writes.
    stripe_customer_id = Column(String(255), unique=True, index=True, nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
