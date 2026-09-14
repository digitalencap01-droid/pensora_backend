from enum import Enum


class ContentTypeEnum(str, Enum):
    BLOG = "blog"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SOCIAL = "social"
    AD = "ad"


class ContentStatusEnum(str, Enum):
    IDEA = "idea"
    DRAFT = "draft"
    GENERATED = "generated"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class ActorTypeEnum(str, Enum):
    USER = "user"
    SYSTEM = "system"
    WORKER = "worker"
    AUTOMATION = "automation"
    AI_AGENT = "ai_agent"


class JobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class DeliveryStatusEnum(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
