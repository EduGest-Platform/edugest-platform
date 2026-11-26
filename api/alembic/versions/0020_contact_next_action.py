"""Add the optional next action (what, who, by when) to CRM contacts (KAN-272)."""
from alembic import op
import sqlalchemy as sa

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('application_event', sa.Column('next_action', sa.String(200), nullable=True))
    op.add_column('application_event', sa.Column('next_action_owner_id', sa.Uuid(), nullable=True))
    op.add_column('application_event', sa.Column('next_action_due_on', sa.Date(), nullable=True))
    op.create_foreign_key('fk_application_event_next_action_owner', 'application_event', 'app_user',
                          ['next_action_owner_id'], ['id'])
    op.create_check_constraint('ck_application_event_next_action', 'application_event',
        "num_nonnulls(next_action, next_action_owner_id, next_action_due_on) = 0 OR "
        "(num_nonnulls(next_action, next_action_owner_id, next_action_due_on) = 3 "
        "AND tipo = 'contacto' AND length(btrim(next_action)) > 0)")


def downgrade():
    op.drop_constraint('ck_application_event_next_action', 'application_event', type_='check')
    op.drop_constraint('fk_application_event_next_action_owner', 'application_event', type_='foreignkey')
    for column in ('next_action_due_on', 'next_action_owner_id', 'next_action'):
        op.drop_column('application_event', column)
