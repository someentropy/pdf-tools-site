import subprocess
import os
from flask import Blueprint, render_template, request, send_file, current_app
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
import pikepdf  # ✅ Add this line
from flask import send_from_directory

app_routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@app_routes.route("/")
def index():
    return render_template("index.html")

@app_routes.route("/download")
def download_file():
    filename = request.args.get("filename")
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


@app_routes.route("/compress", methods=["GET", "POST"])
def compress_pdf():
    if request.method == "POST":
        try:
            file = request.files["file"]
            filename = secure_filename(file.filename)

            level_map = {
                "5": "/screen",     # Most compressed
                "4": "/ebook",
                "3": "/printer",
                "2": "/prepress",
                "1": "/default"     # Best quality, least compression
            }
            selected_level = request.form.get("compression", "3")
            gs_quality = level_map.get(selected_level, "/printer")

            base_dir = os.path.dirname(os.path.dirname(__file__))
            upload_folder = os.path.join(base_dir, "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            input_path = os.path.join(upload_folder, filename)
            compressed_path = os.path.join(upload_folder, "compressed_" + filename)
            file.save(input_path)

            gs_executable = "gswin64c" if os.name == "nt" else "gs"
            gs_command = [
                gs_executable,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={gs_quality}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={compressed_path}",
                input_path,
            ]

            result = subprocess.run(gs_command, capture_output=True, text=True)
            print("Ghostscript stdout:")
            print(result.stdout)
            print("Ghostscript stderr:")
            print(result.stderr)

            if result.returncode != 0:
                return f"Compression failed. Ghostscript error:<br><pre>{result.stderr}</pre>"

            # Compression succeeded — now calculate sizes
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(compressed_path)
            compression_percent = 100 - round((compressed_size / original_size) * 100, 2)

            print(f"Original: {original_size / 1024 / 1024:.2f} MB")
            print(f"Compressed: {compressed_size / 1024 / 1024:.2f} MB")

            return render_template(
                "compress.html",
                auto_download=True,
                download_link="/download?filename=" + "compressed_" + filename,
                original_size=round(original_size / 1024, 2),
                compressed_size=round(compressed_size / 1024, 2),
                compression_percent=compression_percent
            )


        except Exception as e:
            return f"Compression failed: {e}"

    return render_template("compress.html")








@app_routes.route("/merge", methods=["GET", "POST"])
def merge_pdf():
    if request.method == "POST":
        file_keys = ["file1", "file2", "file3", "file4", "file5"]
        merger = PdfMerger()

        uploaded_count = 0

        for key in file_keys:
            file = request.files.get(key)
            if file and file.filename:
                merger.append(file)
                uploaded_count += 1

        if uploaded_count < 2:
            return "Please upload at least 2 PDF files to merge."

        merged_path = os.path.join(UPLOAD_FOLDER, "merged.pdf")
        merger.write(merged_path)
        merger.close()

        return send_file(merged_path, as_attachment=True)

    return render_template("merge.html")



