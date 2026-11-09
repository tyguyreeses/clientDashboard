"""Add additive authentication and security persistence."""
from alembic import op
import sqlalchemy as sa

revision = "20260401_0007"
down_revision = "20260401_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer, primary_key=True), sa.Column("google_subject", sa.String(255), nullable=False, unique=True), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("display_name", sa.String(255)), sa.Column("role", sa.String(20), nullable=False, server_default="admin"), sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_login_at", sa.DateTime(timezone=True)), sa.CheckConstraint("role = 'admin'", name="ck_users_admin_role"))
    op.create_table("sessions", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("csrf_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expiry", "sessions", ["expires_at", "revoked_at"])
    op.create_table("oauth_attempts", sa.Column("id", sa.String(64), primary_key=True), sa.Column("state_hash", sa.String(64), nullable=False, unique=True), sa.Column("nonce_hash", sa.String(64), nullable=False), sa.Column("pkce_challenge", sa.String(128), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)))
    op.create_table("rate_limit_buckets", sa.Column("route_key", sa.String(64), nullable=False), sa.Column("client_ip", sa.String(64), nullable=False), sa.Column("window_start", sa.DateTime(timezone=True), nullable=False), sa.Column("count", sa.Integer, nullable=False), sa.PrimaryKeyConstraint("route_key", "client_ip", "window_start"))
    op.create_table("audit_events", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("event", sa.String(40), nullable=False), sa.Column("outcome", sa.String(20), nullable=False), sa.Column("metadata_json", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_events_created", "audit_events", ["created_at"])
    op.create_table("auth_state", sa.Column("id", sa.Integer, primary_key=True), sa.Column("bootstrap_completed", sa.Boolean, nullable=False, server_default=sa.false()), sa.Column("pending_replacement_email", sa.String(255)), sa.Column("pending_replacement_expires_at", sa.DateTime(timezone=True)), sa.Column("recovery_started_at", sa.DateTime(timezone=True)))
    op.execute("INSERT INTO auth_state (id, bootstrap_completed) VALUES (1, 0)")


def downgrade():
    op.drop_table("auth_state"); op.drop_index("ix_audit_events_created", table_name="audit_events"); op.drop_table("audit_events"); op.drop_table("rate_limit_buckets"); op.drop_table("oauth_attempts"); op.drop_index("ix_sessions_expiry", table_name="sessions"); op.drop_index("ix_sessions_user_id", table_name="sessions"); op.drop_table("sessions"); op.drop_table("users")
