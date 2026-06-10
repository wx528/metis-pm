from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class CommentType:
    NORMAL = "normal"
    MANAGEMENT = "management"
    HANDOVER = "handover"


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    author = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    comment_type = Column(String(20), default=CommentType.NORMAL)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 交接已读回执
    read_by = Column(String(100), nullable=True)   # 谁已读（agent name）
    read_at = Column(DateTime, nullable=True)      # 何时已读

    issue = relationship("Issue", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")
