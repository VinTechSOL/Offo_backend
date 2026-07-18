"""add branch onboarding fields

Revision ID: e5f5ad0a706b
Revises: aab8467f137c
Create Date: 2026-07-13 11:16:57.879240

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "e5f5ad0a706b"
down_revision: Union[str, Sequence[str], None] = "aab8467f137c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =====================================================
    # Cafe Branch Columns
    # =====================================================

    op.add_column(
        "cafe_branch",
        sa.Column("registered_address", sa.Text(), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("business_address", sa.Text(), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("business_type", sa.String(length=50), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("fssai_license_number", sa.String(length=100), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("fssai_license_document_url", sa.Text(), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("gst_registration_number", sa.String(length=100), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("gst_registration_document_url", sa.Text(), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("bank_account_number", sa.String(length=50), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("ifsc_code", sa.String(length=30), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("account_holder_name", sa.String(length=150), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("bank_passbook_url", sa.Text(), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("registered_owner_name", sa.String(length=150), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("owner_phone_number", sa.String(length=20), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        schema="core",
    )

    op.add_column(
        "cafe_branch",
        sa.Column("owner_proof_document_url", sa.Text(), nullable=True),
        schema="core",
    )

    # =====================================================
    # Dynamic Additional Documents
    # =====================================================

    op.create_table(
        "branch_documents",

        sa.Column(
            "document_id",
            sa.BigInteger(),
            primary_key=True,
        ),

        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "core.cafe_branch.branch_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "document_name",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "document_url",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        schema="core",
    )

    # =====================================================
    # Unique Constraints
    # =====================================================

    op.create_unique_constraint(
        "uq_cafeteria_name",
        "cafeteria",
        ["cafe_name"],
        schema="core",
    )

    op.create_unique_constraint(
        "uq_city_campus",
        "campuses",
        ["city_id", "campus_name"],
        schema="locations",
    )

    op.create_unique_constraint(
        "uq_campus_building",
        "buildings",
        ["campus_id", "building_name"],
        schema="locations",
    )

    op.create_unique_constraint(
        "uq_cafe_branch_name",
        "cafe_branch",
        ["cafe_id", "branch_name"],
        schema="core",
    )


def downgrade() -> None:

    # =====================================================
    # Unique Constraints
    # =====================================================

    op.drop_constraint(
        "uq_cafe_branch_name",
        "cafe_branch",
        schema="core",
        type_="unique",
    )

    op.drop_constraint(
        "uq_campus_building",
        "buildings",
        schema="locations",
        type_="unique",
    )

    op.drop_constraint(
        "uq_city_campus",
        "campuses",
        schema="locations",
        type_="unique",
    )

    op.drop_constraint(
        "uq_cafeteria_name",
        "cafeteria",
        schema="core",
        type_="unique",
    )

    # =====================================================
    # Documents Table
    # =====================================================

    op.drop_table(
        "branch_documents",
        schema="core",
    )

    # =====================================================
    # Remove Branch Columns
    # =====================================================

    op.drop_column("cafe_branch", "owner_proof_document_url", schema="core")
    op.drop_column("cafe_branch", "owner_email", schema="core")
    op.drop_column("cafe_branch", "owner_phone_number", schema="core")
    op.drop_column("cafe_branch", "registered_owner_name", schema="core")
    op.drop_column("cafe_branch", "bank_passbook_url", schema="core")
    op.drop_column("cafe_branch", "account_holder_name", schema="core")
    op.drop_column("cafe_branch", "ifsc_code", schema="core")
    op.drop_column("cafe_branch", "bank_account_number", schema="core")
    op.drop_column("cafe_branch", "gst_registration_document_url", schema="core")
    op.drop_column("cafe_branch", "gst_registration_number", schema="core")
    op.drop_column("cafe_branch", "fssai_license_document_url", schema="core")
    op.drop_column("cafe_branch", "fssai_license_number", schema="core")
    op.drop_column("cafe_branch", "business_type", schema="core")
    op.drop_column("cafe_branch", "business_address", schema="core")
    op.drop_column("cafe_branch", "registered_address", schema="core")