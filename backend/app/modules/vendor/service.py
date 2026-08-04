from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.core.s3_service import (
    upload_file,
    validate_upload,
    IMAGE_TYPES,
    DOCUMENT_TYPES,
    MAX_IMAGE_SIZE,
    MAX_DOCUMENT_SIZE,
)

from app.modules.vendor.repository import (
    VendorRepository,
    CafeRepository,
)
from app.modules.locations.repository import LocationRepository
from app.core.time_utils import now_utc


class VendorService:

    @staticmethod
    def create_cafeteria(db: Session, data):
        return VendorRepository.create_cafeteria(db, data)

    @staticmethod
    def list_cafeterias(db: Session):
        return VendorRepository.list_cafeterias(db)

    @staticmethod
    def _process_branch_uploads(
        data,
        image: UploadFile | None = None,
        fssai_document: UploadFile | None = None,
        gst_document: UploadFile | None = None,
        owner_document: UploadFile | None = None,
        bank_passbook: UploadFile | None = None,
    ):
        # -------------------------------------------------
        # Branch Image
        # -------------------------------------------------

        if image:

            validate_upload(
                image,
                allowed_types=IMAGE_TYPES,
                max_size=MAX_IMAGE_SIZE,
            )

            data.image_url = upload_file(
                file_obj=image.file,
                filename=image.filename,
                content_type=image.content_type,
                folder="branches/images",
            )

        # -------------------------------------------------
        # FSSAI
        # -------------------------------------------------

        if fssai_document:

            validate_upload(
                fssai_document,
                allowed_types=DOCUMENT_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
            )

            data.fssai_license_document_url = upload_file(
                file_obj=fssai_document.file,
                filename=fssai_document.filename,
                content_type=fssai_document.content_type,
                folder="branches/documents/fssai",
            )

        # -------------------------------------------------
        # GST
        # -------------------------------------------------

        if gst_document:

            validate_upload(
                gst_document,
                allowed_types=DOCUMENT_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
            )

            data.gst_registration_document_url = upload_file(
                file_obj=gst_document.file,
                filename=gst_document.filename,
                content_type=gst_document.content_type,
                folder="branches/documents/gst",
            )

        # -------------------------------------------------
        # Owner Proof
        # -------------------------------------------------

        if owner_document:

            validate_upload(
                owner_document,
                allowed_types=DOCUMENT_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
            )

            data.owner_proof_document_url = upload_file(
                file_obj=owner_document.file,
                filename=owner_document.filename,
                content_type=owner_document.content_type,
                folder="branches/documents/owner",
            )

        # -------------------------------------------------
        # Bank Passbook
        # -------------------------------------------------

        if bank_passbook:

            validate_upload(
                bank_passbook,
                allowed_types=DOCUMENT_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
            )

            data.bank_passbook_url = upload_file(
                file_obj=bank_passbook.file,
                filename=bank_passbook.filename,
                content_type=bank_passbook.content_type,
                folder="branches/documents/bank",
            )

    @staticmethod
    def _save_additional_documents(
        db: Session,
        branch_id: int,
        documents: list[UploadFile] | None,
    ):

        if not documents:
            return

        for document in documents:

            validate_upload(
                document,
                allowed_types=DOCUMENT_TYPES,
                max_size=MAX_DOCUMENT_SIZE,
            )

            document_url = upload_file(
                file_obj=document.file,
                filename=document.filename,
                content_type=document.content_type,
                folder="branches/documents/other",
            )

            VendorRepository.create_branch_document(
                db=db,
                branch_id=branch_id,
                document_name=document.filename,
                document_url=document_url,
            )


    

    @staticmethod
    def create_branch(
        db: Session,
        data,
        image: UploadFile | None = None,
        fssai_document: UploadFile | None = None,
        gst_document: UploadFile | None = None,
        owner_document: UploadFile | None = None,
        bank_passbook: UploadFile | None = None,
        other_documents: list[UploadFile] | None = None,
    ):

        # -------------------------------------------------
        # Upload Branch Files
        # -------------------------------------------------

        VendorService._process_branch_uploads(
            data=data,
            image=image,
            fssai_document=fssai_document,
            gst_document=gst_document,
            owner_document=owner_document,
            bank_passbook=bank_passbook,
        )

        # -------------------------------------------------
        # Create Branch
        # -------------------------------------------------

        branch = VendorRepository.create_branch(
            db=db,
            data=data,
        )

        # -------------------------------------------------
        # Save Additional Documents
        # -------------------------------------------------

        VendorService._save_additional_documents(
            db=db,
            branch_id=branch.branch_id,
            documents=other_documents,
        )

        return branch

    @staticmethod
    def list_branches(
        db: Session,
        cafe_id: int,
    ):

        rows = VendorRepository.list_branches(
            db,
            cafe_id,
        )

        branches = []

        for row in rows:

            branch = row[0]

            branches.append(
                {
                    "branch_id": branch.branch_id,
                    "cafe_id": branch.cafe_id,
                    "branch_name": branch.branch_name,
                    "city_id": branch.city_id,
                    "city_name": row.city_name,
                    "campus_id": branch.campus_id,
                    "campus_name": row.campus_name,
                    "building_id": branch.building_id,
                    "building_name": row.building_name,
                    "opens_at": branch.opens_at,
                    "closes_at": branch.closes_at,
                    "image_url": branch.image_url,
                    "is_active": branch.is_active,
                    "has_vendor": row.vendor_staff_id is not None,
                }
            )

        return branches

    @staticmethod
    def update_branch(
        db: Session,
        branch_id: int,
        data,
        image: UploadFile | None = None,
        fssai_document: UploadFile | None = None,
        gst_document: UploadFile | None = None,
        owner_document: UploadFile | None = None,
        bank_passbook: UploadFile | None = None,
        other_documents: list[UploadFile] | None = None,
    ):

        # -------------------------------------------------
        # Upload Branch Files
        # -------------------------------------------------

        VendorService._process_branch_uploads(
            data=data,
            image=image,
            fssai_document=fssai_document,
            gst_document=gst_document,
            owner_document=owner_document,
            bank_passbook=bank_passbook,
        )

        # -------------------------------------------------
        # Update Branch
        # -------------------------------------------------

        branch = VendorRepository.update_branch(
            db=db,
            branch_id=branch_id,
            data=data,
        )

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found",
            )

        # -------------------------------------------------
        # Save Additional Documents
        # -------------------------------------------------

        VendorService._save_additional_documents(
            db=db,
            branch_id=branch.branch_id,
            documents=other_documents,
        )

        return branch


    @staticmethod
    def get_branch_by_id(
        db: Session,
        branch_id: int,
    ):
        branch = VendorRepository.get_branch_by_id(
            db=db,
            branch_id=branch_id,
        )

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found",
            )

        return branch


class CafeService:

    @staticmethod
    def get_for_user(
        db: Session,
        user_id: int,
    ):
        context = LocationRepository.get_by_user(
            db,
            user_id,
        )

        if (
            not context
            or not context.city_id
            or not context.campus_id
        ):
            raise HTTPException(
                status_code=400,
                detail="User location context not set",
            )

        return CafeRepository.get_for_user_context(
            db,
            city_id=context.city_id,
            campus_id=context.campus_id,
            building_id=context.building_id,
        )

    @staticmethod
    def is_branch_open(branch):
        if not branch.opens_at or not branch.closes_at:
            return True

        now = now_utc().time()
        return branch.opens_at <= now <= branch.closes_at