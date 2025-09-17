"""remove_rag_chunks_table

Revision ID: ce0b87a51f9c
Revises: 99afbe69a92f
Create Date: 2025-09-15 23:19:07.410326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce0b87a51f9c'
down_revision: Union[str, None] = '99afbe69a92f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove rag_chunks table as all chunk data is now stored in Qdrant vector database
    op.drop_table('rag_chunks')


def downgrade() -> None:
    # Recreate rag_chunks table for rollback (if needed)
    op.create_table('rag_chunks',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('rag_document_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('content', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('chunk_index', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('token_count', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('page_number', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('section_title', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('embedding_vector', sa.JSON(), autoincrement=False, nullable=True),
        sa.Column('embedding_model', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('chunk_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('chunk_metadata', sa.JSON(), autoincrement=False, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['rag_document_id'], ['rag_documents.id'], name='rag_chunks_rag_document_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='rag_chunks_pkey')
    )
    op.create_index('ix_rag_chunks_id', 'rag_chunks', ['id'], unique=False)
