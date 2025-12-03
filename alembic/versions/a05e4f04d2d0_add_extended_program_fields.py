"""add_extended_program_fields

Revision ID: a05e4f04d2d0
Revises: 54f3f673542c
Create Date: 2025-11-25 13:55:20.405610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a05e4f04d2d0'
down_revision: Union[str, None] = '54f3f673542c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('uk_programs', sa.Column('duolingo_min_score', sa.Float(), nullable=True))
    op.add_column('uk_programs', sa.Column('moi_accepted', sa.String(), nullable=True))
    op.add_column('uk_programs', sa.Column('initial_deposit_gbp', sa.Float(), nullable=True))
    op.add_column('uk_programs', sa.Column('scholarships', sa.Text(), nullable=True))
    op.add_column('uk_programs', sa.Column('study_gap_acceptable', sa.String(), nullable=True))
    op.add_column('uk_programs', sa.Column('special_notes', sa.Text(), nullable=True))
    op.add_column('uk_programs', sa.Column('entry_requirements_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('uk_programs', 'entry_requirements_text')
    op.drop_column('uk_programs', 'special_notes')
    op.drop_column('uk_programs', 'study_gap_acceptable')
    op.drop_column('uk_programs', 'scholarships')
    op.drop_column('uk_programs', 'initial_deposit_gbp')
    op.drop_column('uk_programs', 'moi_accepted')
    op.drop_column('uk_programs', 'duolingo_min_score')
