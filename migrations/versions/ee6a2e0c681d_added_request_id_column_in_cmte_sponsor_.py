"""added request_id column in cmte_sponsor_docs table

Revision ID: ee6a2e0c681d
Revises: c3136206827f
Create Date: 2025-03-01 09:23:03.232499

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee6a2e0c681d'
down_revision = 'c3136206827f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cmte_sponsor_docs', sa.Column('request_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'cmte_sponsor_docs', 'cmte_sponsor_requests', ['request_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'cmte_sponsor_docs', type_='foreignkey')
    op.drop_column('cmte_sponsor_docs', 'request_id')
    # ### end Alembic commands ###
