"""KAN-275: origin channel and author of every application.

Applications that already exist arrived through the public form, the only intake there was (or are synthetic seed rows).
Their author is copied from the creation event; it stays empty for the form sent without a session.

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application", sa.Column("origin_channel", sa.String(20), nullable=False, server_default="formulario"))
    op.add_column("application", sa.Column("created_by", sa.Uuid(), nullable=True))
    # The creation event already kept the account of whoever sent the form with a session.
    op.execute(
        "UPDATE application SET created_by = event.actor_user_id FROM application_event AS event "
        "WHERE event.application_id = application.id AND event.tipo = 'creada' AND event.actor_user_id IS NOT NULL"
    )
    op.create_foreign_key("fk_application_created_by", "application", "app_user", ["created_by"], ["id"])
    op.create_check_constraint(
        "ck_application_origin_channel", "application",
        "origin_channel IN ('formulario', 'correo', 'telefono', 'derivacion', 'registro_manual', 'redes')",
    )
    op.create_check_constraint("ck_application_manual_author", "application", "origin_channel = 'formulario' OR created_by IS NOT NULL")


def downgrade() -> None:
    """Drops the channel and author of each application.

    Upgrading again would label every application as «formulario»: the real channel and author of the manual ones
    survive only in the `application.created` audit events (`origin_channel` and the actor), to be restored by hand.
    """
    op.drop_constraint("ck_application_manual_author", "application", type_="check")
    op.drop_constraint("ck_application_origin_channel", "application", type_="check")
    op.drop_constraint("fk_application_created_by", "application", type_="foreignkey")
    op.drop_column("application", "created_by")
    op.drop_column("application", "origin_channel")
