"""add discipline to eligibility assessment

Revision ID: 9999_add_discipline
Revises: 316366e80809
Create Date: 2025-09-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9999_add_discipline'
down_revision: Union[str, None] = '316366e80809'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('eligibility_assessments', sa.Column('discipline', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('eligibility_assessments', 'discipline')


