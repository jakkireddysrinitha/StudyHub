from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    request,
    jsonify,
    send_file
)

from flask_login import current_user
from werkzeug.utils import secure_filename

from src.config import RESOURCE_DIR

from src.models import db, Resource

from src.rag import (
    process_pdf,
    delete_resource as delete_chroma_resource,
    search_resources,
    get_resource_documents
)

from src.ai import (
    generate_answer,
    generate_summary
)


api = Blueprint(
    "api",
    __name__
)


# ============================================================
# HELPERS
# ============================================================

def user_resource_dir():
    """
    Return the resource directory for the
    currently logged-in user.
    """

    path = RESOURCE_DIR / str(
        current_user.id
    )

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return path


def user_is_logged_in():
    """
    Protect API routes from unauthenticated access.
    """

    if not current_user.is_authenticated:
        return jsonify({
            "error": "Authentication required."
        }), 401

    return None


def get_user_resource(filename):
    """
    Find a resource only if it belongs
    to the currently logged-in user.
    """

    return Resource.query.filter_by(
        user_id=current_user.id,
        title=filename
    ).first()


def serialize_resource(resource):
    """
    Convert database Resource into the
    format expected by the frontend.
    """

    file_path = (
        user_resource_dir()
        / resource.filename
    )

    size = 0

    if file_path.exists():
        size = file_path.stat().st_size

    uploaded_at = resource.uploaded_at

    if isinstance(
        uploaded_at,
        datetime
    ):
        uploaded_at = uploaded_at.strftime(
            "%Y-%m-%d %H:%M"
        )

    return {
        "name": resource.title,
        "category": resource.category,
        "size": size,
        "uploaded_at": uploaded_at
    }


def search_user_resources(
    question,
    resources,
    n_results=5
):
    """
    Search only resources owned by the
    current user.

    Returns a Chroma-style result dictionary
    so generate_answer() can consume it.
    """

    all_documents = []
    all_metadatas = []
    all_distances = []

    for resource in resources:

        try:
            result = search_resources(
                question,
                filename=resource.filename,
                n_results=n_results
            )

            if not isinstance(
                result,
                dict
            ):
                continue

            documents_groups = result.get(
                "documents",
                []
            )

            metadatas_groups = result.get(
                "metadatas",
                []
            )

            distances_groups = result.get(
                "distances",
                []
            )

            if not documents_groups:
                continue

            documents = documents_groups[0]

            metadatas = (
                metadatas_groups[0]
                if metadatas_groups
                else []
            )

            distances = (
                distances_groups[0]
                if distances_groups
                else []
            )

            for index, document in enumerate(
                documents
            ):

                metadata = {}

                if index < len(metadatas):
                    metadata = (
                        metadatas[index]
                        or {}
                    )

                # Store the user-visible filename
                # instead of exposing the internal
                # generated filename to the AI.
                metadata = dict(metadata)

                metadata["source"] = (
                    resource.title
                )

                all_documents.append(
                    document
                )

                all_metadatas.append(
                    metadata
                )

                if index < len(distances):
                    all_distances.append(
                        distances[index]
                    )
                else:
                    all_distances.append(
                        float("inf")
                    )

        except Exception as error:

            print(
                "RESOURCE SEARCH ERROR:",
                resource.filename,
                error
            )

    # --------------------------------------------------------
    # Sort results by similarity distance.
    # Lower distance = more relevant.
    # --------------------------------------------------------

    combined = list(
        zip(
            all_documents,
            all_metadatas,
            all_distances
        )
    )

    combined.sort(
        key=lambda item: item[2]
    )

    combined = combined[
        :n_results
    ]

    documents = [
        item[0]
        for item in combined
    ]

    metadatas = [
        item[1]
        for item in combined
    ]

    distances = [
        item[2]
        for item in combined
    ]

    # --------------------------------------------------------
    # Return exactly the structure expected
    # by generate_answer()
    # --------------------------------------------------------

    return {
        "documents": [
            documents
        ],
        "metadatas": [
            metadatas
        ],
        "distances": [
            distances
        ]
    }


# ============================================================
# GET RESOURCES
# ============================================================

@api.route(
    "/resources",
    methods=["GET"]
)
def get_resources():

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resources = (
            Resource.query
            .filter_by(
                user_id=current_user.id
            )
            .order_by(
                Resource.uploaded_at.desc()
            )
            .all()
        )

        return jsonify([
            serialize_resource(resource)
            for resource in resources
        ])

    except Exception as error:

        print(
            "GET RESOURCES ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# UPLOAD RESOURCE
# ============================================================

@api.route(
    "/resources",
    methods=["POST"]
)
def upload_resource():

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        if "file" not in request.files:
            return jsonify({
                "error": "No file was uploaded."
            }), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({
                "error": "Please select a file."
            }), 400

        original_filename = (
            file.filename.strip()
        )

        safe_filename = secure_filename(
            original_filename
        )

        if not safe_filename:
            return jsonify({
                "error": "Invalid filename."
            }), 400

        if not safe_filename.lower().endswith(
            ".pdf"
        ):
            return jsonify({
                "error": "Only PDF files are supported."
            }), 400

        # ----------------------------------------------------
        # Create a unique internal filename.
        # ----------------------------------------------------

        stored_filename = (
            f"user_{current_user.id}_"
            f"{uuid4().hex}_"
            f"{safe_filename}"
        )

        user_dir = user_resource_dir()

        file_path = (
            user_dir
            / stored_filename
        )

        file.save(
            file_path
        )

        # ----------------------------------------------------
        # Process through RAG.
        # ----------------------------------------------------

        try:

            processed_resource = process_pdf(
                file_path
            )

        except Exception:

            if file_path.exists():
                file_path.unlink()

            raise

        # ----------------------------------------------------
        # Replace existing resource with same visible name.
        # ----------------------------------------------------

        existing_resource = (
            Resource.query
            .filter_by(
                user_id=current_user.id,
                title=original_filename
            )
            .first()
        )

        if existing_resource:

            old_file_path = (
                user_dir
                / existing_resource.filename
            )

            try:

                delete_chroma_resource(
                    existing_resource.filename
                )

            except Exception as error:

                print(
                    "OLD CHROMA DELETE ERROR:",
                    error
                )

            if old_file_path.exists():
                old_file_path.unlink()

            db.session.delete(
                existing_resource
            )

        # ----------------------------------------------------
        # Create DB record.
        # ----------------------------------------------------

        category = "General Study"

        if isinstance(
            processed_resource,
            dict
        ):
            category = processed_resource.get(
                "category",
                "General Study"
            )

        resource = Resource(
            filename=stored_filename,
            title=original_filename,
            category=category,
            uploaded_at=datetime.now(),
            user_id=current_user.id
        )

        db.session.add(
            resource
        )

        db.session.commit()

        return jsonify(
            serialize_resource(resource)
        ), 201

    except Exception as error:

        db.session.rollback()

        print(
            "UPLOAD ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# PREVIEW RESOURCE
# ============================================================

@api.route(
    "/resources/<path:filename>/preview",
    methods=["GET"]
)
def preview_resource(filename):

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resource = get_user_resource(
            filename
        )

        if not resource:
            return jsonify({
                "error": "Resource not found."
            }), 404

        file_path = (
            user_resource_dir()
            / resource.filename
        )

        if not file_path.exists():
            return jsonify({
                "error": "Resource file not found."
            }), 404

        return send_file(
            file_path,
            mimetype="application/pdf"
        )

    except Exception as error:

        print(
            "PREVIEW ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# DOWNLOAD RESOURCE
# ============================================================

@api.route(
    "/resources/<path:filename>/download",
    methods=["GET"]
)
def download_resource(filename):

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resource = get_user_resource(
            filename
        )

        if not resource:
            return jsonify({
                "error": "Resource not found."
            }), 404

        file_path = (
            user_resource_dir()
            / resource.filename
        )

        if not file_path.exists():
            return jsonify({
                "error": "Resource file not found."
            }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=resource.title
        )

    except Exception as error:

        print(
            "DOWNLOAD ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# DELETE ONE RESOURCE
# ============================================================

@api.route(
    "/resources/<path:filename>",
    methods=["DELETE"]
)
def delete_resource_route(filename):

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resource = get_user_resource(
            filename
        )

        if not resource:
            return jsonify({
                "error": "Resource not found."
            }), 404

        file_path = (
            user_resource_dir()
            / resource.filename
        )

        # Delete from Chroma.
        try:

            delete_chroma_resource(
                resource.filename
            )

        except Exception as error:

            print(
                "CHROMA DELETE ERROR:",
                error
            )

        # Delete physical file.
        if file_path.exists():
            file_path.unlink()

        # Delete DB record.
        db.session.delete(
            resource
        )

        db.session.commit()

        return jsonify({
            "message": "Resource deleted successfully."
        })

    except Exception as error:

        db.session.rollback()

        print(
            "DELETE ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# DELETE ALL USER RESOURCES
# ============================================================

@api.route(
    "/resources",
    methods=["DELETE"]
)
def delete_all_resources_route():

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resources = (
            Resource.query
            .filter_by(
                user_id=current_user.id
            )
            .all()
        )

        user_dir = user_resource_dir()

        for resource in resources:

            try:

                delete_chroma_resource(
                    resource.filename
                )

            except Exception as error:

                print(
                    "CHROMA DELETE ERROR:",
                    resource.filename,
                    error
                )

            file_path = (
                user_dir
                / resource.filename
            )

            if file_path.exists():
                file_path.unlink()

            db.session.delete(
                resource
            )

        db.session.commit()

        return jsonify({
            "message": (
                "All resources deleted successfully."
            )
        })

    except Exception as error:

        db.session.rollback()

        print(
            "DELETE ALL ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# ASK AI
# ============================================================

@api.route(
    "/ask",
    methods=["POST"]
)
def ask_ai():

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        data = request.get_json(
            silent=True
        ) or {}

        question = str(
            data.get(
                "question",
                ""
            )
        ).strip()

        resource_name = str(
            data.get(
                "resource",
                ""
            )
        ).strip()

        category = str(
            data.get(
                "category",
                ""
            )
        ).strip()

        if not question:

            return jsonify({
                "error": "Please enter a question."
            }), 400

        # ----------------------------------------------------
        # Search inside one specific user resource.
        # ----------------------------------------------------

        if resource_name:

            resource = get_user_resource(
                resource_name
            )

            if not resource:

                return jsonify({
                    "error": "Resource not found."
                }), 404

            search_results = (
                search_user_resources(
                    question,
                    [resource],
                    n_results=5
                )
            )

        # ----------------------------------------------------
        # Search inside the selected category.
        # ----------------------------------------------------

        elif category:

            resources = (
                Resource.query
                .filter_by(
                    user_id=current_user.id,
                    category=category
                )
                .all()
            )

            search_results = (
                search_user_resources(
                    question,
                    resources,
                    n_results=5
                )
            )

        # ----------------------------------------------------
        # Search all resources belonging
        # to the current user.
        # ----------------------------------------------------

        else:

            resources = (
                Resource.query
                .filter_by(
                    user_id=current_user.id
                )
                .all()
            )

            search_results = (
                search_user_resources(
                    question,
                    resources,
                    n_results=5
                )
            )

        result = generate_answer(
            question,
            search_results
        )

        return jsonify(
            result
        )

    except Exception as error:

        print(
            "ASK AI ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# SUMMARY
# ============================================================

@api.route(
    "/resources/<path:filename>/summary",
    methods=["GET"]
)
def summarize_resource(filename):

    auth_error = user_is_logged_in()

    if auth_error:
        return auth_error

    try:

        resource = get_user_resource(
            filename
        )

        if not resource:

            return jsonify({
                "error": "Resource not found."
            }), 404

        documents = get_resource_documents(
            resource.filename
        )

        summary = generate_summary(
            resource.title,
            documents
        )

        return jsonify({
            "filename": resource.title,
            "summary": summary
        })

    except Exception as error:

        print(
            "SUMMARY ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500