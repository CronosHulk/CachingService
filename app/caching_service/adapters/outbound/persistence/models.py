import uuid

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransformCache(Base):
    __tablename__ = "transform_cache"

    input_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)


class Payload(Base):
    __tablename__ = "payload"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    output: Mapped[str] = mapped_column(Text, nullable=False)
