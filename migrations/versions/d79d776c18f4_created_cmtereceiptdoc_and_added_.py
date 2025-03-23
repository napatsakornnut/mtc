"""created CMTEReceiptDoc and added disable_at columns in cmte_event_sponsors in table

Revision ID: d79d776c18f4
Revises: db8ed93776b5
Create Date: 2025-03-23 13:43:32.520571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd79d776c18f4'
down_revision = 'db8ed93776b5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cmte_receipt_docs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('request_id', sa.Integer(), nullable=True),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('filename', sa.Text(), nullable=False),
    sa.Column('upload_datetime', sa.DateTime(timezone=True), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['request_id'], ['cmte_sponsor_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('cmte_event_sponsors', sa.Column('disable_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cmte_event_sponsors_version', sa.Column('disable_at', sa.DateTime(timezone=True), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cmte_event_sponsors_version', 'disable_at')
    op.drop_column('cmte_event_sponsors', 'disable_at')
    op.drop_table('cmte_receipt_docs')
    # ### end Alembic commands ###
