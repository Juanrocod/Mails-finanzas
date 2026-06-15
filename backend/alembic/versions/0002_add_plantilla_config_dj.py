"""add plantilla and config_dj tables

Revision ID: 0002
Revises: ed7df405935c
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = 'ed7df405935c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plantilla',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'config_dj',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activa', sa.Boolean(), nullable=False),
        sa.Column('incluir_texto_en_minuta', sa.Boolean(), nullable=False),
        sa.Column('texto_alerta', sa.Text(), nullable=False),
        sa.Column('reglas', sa.Text(), nullable=False),
        sa.Column('logica', sa.String(length=3), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('config_dj')
    op.drop_table('plantilla')
