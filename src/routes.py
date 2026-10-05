import json
from datetime import datetime

from flask import (
    Blueprint,
    request,
    jsonify,
    send_file
)

from src.config import (
    RESOURCE_DIR,
    METADATA_FILE
)

from src.rag import (
    process_pdf,
    delete_resource as delete_chroma_resource,
    delete_all_resources,
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


def load_resources():
    if not METADATA_FILE.exists():
        return []

    try:
        with open(
            METADATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return []


def save_resources(resources):
    RESOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            resources,
            file,
            indent=4,
            ensure_ascii=False
        )


@api.route(
    "/resources",
    methods=["GET"]
)
def get_resources():
    try:
        resources = load_resources()

        return jsonify(
            resources
        )

    except Exception as error:
        print(
            "GET RESOURCES ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


@api.route(
    "/resources",
    methods=["POST"]
)
def upload_resource():
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

        filename = file.filename.strip()

        if not filename.lower().endswith(".pdf"):
            return jsonify({
                "error": "Only PDF files are supported."
            }), 400

        file_path = RESOURCE_DIR / filename

        file.save(
            file_path
        )

        try:
            processed_resource = process_pdf(
                file_path
            )

        except Exception:
            if file_path.exists():
                file_path.unlink()

            raise

        resources = load_resources()

        resources = [
            resource
            for resource in resources
            if resource.get("name") != filename
        ]

        stat = file_path.stat()

        resource_data = {
            "name": processed_resource["name"],
            "category": processed_resource["category"],
            "size": stat.st_size,
            "uploaded_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        }

        resources.append(
            resource_data
        )

        save_resources(
            resources
        )

        return jsonify(
            resource_data
        ), 201

    except Exception as error:
        print(
            "UPLOAD ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


@api.route(
    "/resources/<path:filename>/preview",
    methods=["GET"]
)
def preview_resource(filename):
    try:
        file_path = RESOURCE_DIR / filename

        if not file_path.exists():
            return jsonify({
                "error": "Resource not found."
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


@api.route(
    "/resources/<path:filename>/download",
    methods=["GET"]
)
def download_resource(filename):
    try:
        file_path = RESOURCE_DIR / filename

        if not file_path.exists():
            return jsonify({
                "error": "Resource not found."
            }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as error:
        print(
            "DOWNLOAD ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


@api.route(
    "/resources/<path:filename>",
    methods=["DELETE"]
)
def delete_resource_route(filename):
    try:
        delete_chroma_resource(
            filename
        )

        file_path = RESOURCE_DIR / filename

        if file_path.exists():
            file_path.unlink()

        resources = load_resources()

        resources = [
            resource
            for resource in resources
            if resource.get("name") != filename
        ]

        save_resources(
            resources
        )

        return jsonify({
            "message": "Resource deleted successfully."
        })

    except Exception as error:
        print(
            "DELETE ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


@api.route(
    "/resources",
    methods=["DELETE"]
)
def delete_all_resources_route():
    try:
        delete_all_resources()

        resources = load_resources()

        for resource in resources:
            filename = resource.get("name")

            if filename:
                file_path = RESOURCE_DIR / filename

                if file_path.exists():
                    file_path.unlink()

        save_resources([])

        return jsonify({
            "message": "All resources deleted successfully."
        })

    except Exception as error:
        print(
            "DELETE ALL ERROR:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


@api.route(
    "/ask",
    methods=["POST"]
)
def ask_ai():
    try:
        data = request.get_json(
            silent=True
        ) or {}

        question = str(
            data.get("question", "")
        ).strip()

        resource = str(
            data.get("resource", "")
        ).strip()

        category = str(
            data.get("category", "")
        ).strip()

        if not question:
            return jsonify({
                "error": "Please enter a question."
            }), 400

        if resource:
            search_results = search_resources(
                question,
                filename=resource,
                n_results=5
            )

        elif category:
            search_results = search_resources(
                question,
                category=category,
                n_results=5
            )

        else:
            search_results = search_resources(
                question,
                n_results=5
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


@api.route(
    "/resources/<path:filename>/summary",
    methods=["GET"]
)
def summarize_resource(filename):
    try:
        documents = get_resource_documents(
            filename
        )

        summary = generate_summary(
            filename,
            documents
        )

        return jsonify({
            "filename": filename,
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