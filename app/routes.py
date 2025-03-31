import os
from flask import Blueprint, render_template, request, send_file
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from werkzeug.utils import secure_filename

app_routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = "uploads"

@app_routes.route("/")
def index():
    return render_template("index.html")

@app_routes.route("/compress", methods=["GET", "POST"])
def compress_pdf():
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        reader = PdfReader(filepath)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        compressed_path = os.path.join(UPLOAD_FOLDER, "compressed_" + filename)
        with open(compressed_path, "wb") as f:
            writer.write(f)

        return send_file(compressed_path, as_attachment=True)
    return render_template("compress.html")

@app_routes.route("/merge", methods=["GET", "POST"])
def merge_pdf():
    if request.method == "POST":
        files = request.files.getlist("files")
        merger = PdfMerger()
        for file in files:
            merger.append(file)

        merged_path = os.path.join(UPLOAD_FOLDER, "merged.pdf")
        merger.write(merged_path)
        merger.close()
        return send_file(merged_path, as_attachment=True)
    return render_template("merge.html")
