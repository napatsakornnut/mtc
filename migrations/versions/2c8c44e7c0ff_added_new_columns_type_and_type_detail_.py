"""added new columns (type and type_detail) in CMTEEventSponsor table

Revision ID: 2c8c44e7c0ff
Revises: 1e69a5955913
Create Date: 2025-02-08 17:07:53.103791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c8c44e7c0ff'
down_revision = '1e69a5955913'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cmte_event_sponsors', sa.Column('type', sa.String(), nullable=True))
    op.add_column('cmte_event_sponsors', sa.Column('type_detail', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cmte_event_sponsors', 'type_detail')
    op.drop_column('cmte_event_sponsors', 'type')
    # ### end Alembic commands ###
