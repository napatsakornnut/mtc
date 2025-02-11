"""added transaction history

Revision ID: 65aa6acbdf35
Revises: 2c8c44e7c0ff
Create Date: 2025-02-11 16:06:09.075410

"""
import sqlalchemy_utils
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '65aa6acbdf35'
down_revision = '2c8c44e7c0ff'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cmte_event_sponsors_version',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('old_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('name', sa.String(), autoincrement=False, nullable=False),
    sa.Column('code', sa.String(), autoincrement=False, nullable=True),
    sa.Column('affiliation', sa.String(), autoincrement=False, nullable=True),
    sa.Column('address', sa.Text(), autoincrement=False, nullable=True),
    sa.Column('zipcode', sa.String(), autoincrement=False, nullable=True),
    sa.Column('telephone', sa.String(), autoincrement=False, nullable=True),
    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), autoincrement=False, nullable=True),
    sa.Column('website', sa.String(), autoincrement=False, nullable=True),
    sa.Column('registered_datetime', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
    sa.Column('expire_date', sa.Date(), autoincrement=False, nullable=True),
    sa.Column('type', sa.String(), autoincrement=False, nullable=True),
    sa.Column('type_detail', sa.String(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_cmte_event_sponsors_version_end_transaction_id'), 'cmte_event_sponsors_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_cmte_event_sponsors_version_operation_type'), 'cmte_event_sponsors_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_cmte_event_sponsors_version_transaction_id'), 'cmte_event_sponsors_version', ['transaction_id'], unique=False)
    op.create_table('cmte_sponsor_members_version',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('old_user_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('title', sa.String(), autoincrement=False, nullable=True),
    sa.Column('firstname', sa.String(), autoincrement=False, nullable=True),
    sa.Column('lastname', sa.String(), autoincrement=False, nullable=True),
    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), autoincrement=False, nullable=True),
    sa.Column('_password_hash', sa.String(length=255), autoincrement=False, nullable=True),
    sa.Column('mobile_phone', sa.String(), autoincrement=False, nullable=True),
    sa.Column('telephone', sa.String(), autoincrement=False, nullable=True),
    sa.Column('position', sa.String(), autoincrement=False, nullable=True),
    sa.Column('sponsor_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('is_coordinator', sa.Boolean(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_cmte_sponsor_members_version_end_transaction_id'), 'cmte_sponsor_members_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_cmte_sponsor_members_version_operation_type'), 'cmte_sponsor_members_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_cmte_sponsor_members_version_transaction_id'), 'cmte_sponsor_members_version', ['transaction_id'], unique=False)
    op.create_table('sponsor_qualification_assoc_version',
    sa.Column('event_sponsor_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('qualification_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('transaction_id')
    )
    op.create_index(op.f('ix_sponsor_qualification_assoc_version_end_transaction_id'), 'sponsor_qualification_assoc_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_sponsor_qualification_assoc_version_operation_type'), 'sponsor_qualification_assoc_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_sponsor_qualification_assoc_version_transaction_id'), 'sponsor_qualification_assoc_version', ['transaction_id'], unique=False)
    op.create_table('transaction',
    sa.Column('issued_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('remote_addr', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('transaction')
    op.drop_index(op.f('ix_sponsor_qualification_assoc_version_transaction_id'), table_name='sponsor_qualification_assoc_version')
    op.drop_index(op.f('ix_sponsor_qualification_assoc_version_operation_type'), table_name='sponsor_qualification_assoc_version')
    op.drop_index(op.f('ix_sponsor_qualification_assoc_version_end_transaction_id'), table_name='sponsor_qualification_assoc_version')
    op.drop_table('sponsor_qualification_assoc_version')
    op.drop_index(op.f('ix_cmte_sponsor_members_version_transaction_id'), table_name='cmte_sponsor_members_version')
    op.drop_index(op.f('ix_cmte_sponsor_members_version_operation_type'), table_name='cmte_sponsor_members_version')
    op.drop_index(op.f('ix_cmte_sponsor_members_version_end_transaction_id'), table_name='cmte_sponsor_members_version')
    op.drop_table('cmte_sponsor_members_version')
    op.drop_index(op.f('ix_cmte_event_sponsors_version_transaction_id'), table_name='cmte_event_sponsors_version')
    op.drop_index(op.f('ix_cmte_event_sponsors_version_operation_type'), table_name='cmte_event_sponsors_version')
    op.drop_index(op.f('ix_cmte_event_sponsors_version_end_transaction_id'), table_name='cmte_event_sponsors_version')
    op.drop_table('cmte_event_sponsors_version')
    # ### end Alembic commands ###
