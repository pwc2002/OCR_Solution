"""change_default_lang_to_en

Revision ID: 002_change_default_lang
Revises: 001_initial
Create Date: 2024-11-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_change_default_lang'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # jobs 테이블의 lang 컬럼 기본값을 'en'으로 변경
    # Note: SQLite에서는 alter_column 제한이 있을 수 있으나 PostgreSQL에서는 작동함
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.alter_column('lang', server_default='en')


def downgrade() -> None:
    # jobs 테이블의 lang 컬럼 기본값을 'ko'로 복구
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.alter_column('lang', server_default='ko')

