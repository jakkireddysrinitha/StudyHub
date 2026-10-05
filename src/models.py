from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    resources = db.relationship(
        "Resource",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Resource(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False,
        default="General"
    )

    uploaded_at = db.Column(
        db.DateTime,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    user = db.relationship(
        "User",
        back_populates="resources"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "filename",
            name="unique_user_resource"
        ),
    )