"""merge heads for discipline

Revision ID: 03e591f539f2
Revises: 42f6523de440, 9999_add_discipline
Create Date: 2025-09-08 22:01:48.381303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03e591f539f2'
down_revision: Union[str, None] = ('42f6523de440', '9999_add_discipline')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
