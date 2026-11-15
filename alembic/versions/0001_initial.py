"""LSK access and audit schema, revision 0001_initial."""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("access_requests",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("tenant_id",sa.String(100),nullable=False),
      sa.Column("requester",sa.String(200),nullable=False),
      sa.Column("resource",sa.String(200),nullable=False),
      sa.Column("permission",sa.String(50),nullable=False),
      sa.Column("justification",sa.String(1000),nullable=False),
      sa.Column("status",sa.String(30),nullable=False),
      sa.Column("decided_by",sa.String(200),nullable=True))
    op.create_index("ix_access_requests_tenant_id","access_requests",["tenant_id"])
    op.create_table("audit_events",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("tenant_id",sa.String(100),nullable=False),
      sa.Column("actor",sa.String(200),nullable=False),
      sa.Column("action",sa.String(60),nullable=False),
      sa.Column("subject",sa.String(36),nullable=False))
    op.create_index("ix_audit_events_tenant_id","audit_events",["tenant_id"])

def downgrade():
    op.drop_index("ix_audit_events_tenant_id",table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_access_requests_tenant_id",table_name="access_requests")
    op.drop_table("access_requests")
