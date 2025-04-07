
import subprocess
import os
import zipfile  # New import for PDF splitting
from flask import Blueprint, render_template, request, send_file, current_app, redirect, url_for
from PyPDF2 import PdfMerger, PdfReader, PdfWriter  # Update PyPDF2 imports for splitting
from werkzeug.utils import secure_filename
import pikepdf
from flask import send_from_directory
import json
import os
from datetime import datetime
from flask import flash, redirect, url_for, jsonify

app_routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

from flask import request, redirect

@app_routes.before_request
def redirect_www_and_root_domains():
    host = request.host.lower()
    path = request.path.lower()
    user_agent = request.headers.get("User-Agent", "").lower()

    # Let bots through for verification
    if "googlebot" in user_agent or "adsense" in user_agent:
        return  # allow crawlers
    
    # For all users including bots, ensure canonical consistency
    if host == "carbonpdf.com" or host == "www.carbonpdf.com":
        return redirect("https://freepdftools.carbonprojects.dev" + request.full_path, code=301)
    
    # Redirect www → root domain
    if host == "www.carbonprojects.dev":
        new_url = request.url.replace("://www.", "://", 1)
        return redirect(new_url, code=301)

    # Let "/" and "/ads.txt" on root domain serve locally
    if host == "carbonprojects.dev" and path in ["/", "/ads.txt"]:
        return  # allow Flask to handle it normally

    # Redirect everything else from root domain
    if host == "carbonprojects.dev":
        return redirect("https://freepdftools.carbonprojects.dev" + request.full_path, code=301)


@app_routes.route("/", methods=["GET"])
def index():
    if request.host.lower() == "carbonprojects.dev":
        return render_template("root_home.html")
    return render_template("index.html")


@app_routes.route("/download")
def download_file():
    filename = request.args.get("filename")
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# Add redirects from old URLs to new URLs
@app_routes.route("/compress")
def compress_redirect():
    return redirect(url_for('routes.compress_pdf_online'), code=301)


@app_routes.route("/merge")
def merge_redirect():
    return redirect(url_for('routes.merge_pdf_files'), code=301)


# New SEO-friendly URL for compress
@app_routes.route("/compress-pdf-online", methods=["GET", "POST"])
def compress_pdf_online():
    # Define the maximum file size (20 MB)
    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
    
    if request.method == "POST":
        try:
            # Check if file part exists in request
            if "file" not in request.files:
                return render_template("compress.html", error="No file part in the request")
            
            file = request.files["file"]
            
            # Check if a file was selected
            if file.filename == "":
                return render_template("compress.html", error="No file selected")
            
            # Check file size (server-side validation)
            file.seek(0, 2)  # Go to the end of the file
            file_size = file.tell()  # Get current position (file size)
            file.seek(0)  # Reset file position to beginning
            
            # If file size exceeds limit, return error
            if file_size > MAX_FILE_SIZE_BYTES:
                return render_template(
                    "compress.html", 
                    error=f"File size exceeds the maximum limit of 20 MB. Your file is {file_size / (1024 * 1024):.2f} MB"
                )
            
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


# New SEO-friendly URL for merge
@app_routes.route("/merge-pdf-files", methods=["GET", "POST"])
def merge_pdf_files():
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


# New routes for the additional content pages
@app_routes.route("/pdf-file-size-guide")
def pdf_file_size_guide():
    return render_template("pdf-file-size-guide.html")


@app_routes.route("/pdf-accessibility-guide")
def pdf_accessibility_guide():
    return render_template("pdf-accessibility-guide.html")


# Routes for the existing pages mentioned in the footer
@app_routes.route("/about")
def about():
    return render_template("about.html")


@app_routes.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app_routes.route("/terms")
def terms():
    return render_template("terms.html")


# Updated contact route with support for AJAX and more fields
@app_routes.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            # Extract form data
            name = request.form.get("name", "")
            email = request.form.get("email", "")
            subject = request.form.get("subject", "")
            message = request.form.get("message", "")
            
            # Create messages directory on the volume
            messages_dir = "/app/messages"  # This is where the volume is mounted
            os.makedirs(messages_dir, exist_ok=True)
            
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{email.replace('@', '_at_')}.json"
            
            # Create the message data structure
            message_data = {
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save the message to the volume
            message_path = os.path.join(messages_dir, filename)
            with open(message_path, 'w') as f:
                json.dump(message_data, f, indent=4)
            
            return redirect(url_for('routes.contact', success='true'))
            
        except Exception as e:
            print(f"Error saving contact message: {e}")
            return render_template("contact.html", error="Sorry, there was an error processing your message. Please try again later.")
    
    # GET request
    success = request.args.get('success') == 'true'
    return render_template("contact.html", success=success)


# Generate a sitemap.xml dynamically
# Update this function in routes.py

@app_routes.route("/sitemap.xml")
def sitemap():
    """Generate a dynamic sitemap."""
    pages = [
        {"loc": "/", "priority": "1.0"},
        {"loc": "/compress-pdf-online", "priority": "0.8"},
        {"loc": "/merge-pdf-files", "priority": "0.8"},
        {"loc": "/split-pdf", "priority": "0.8"},
        {"loc": "/pdf-file-size-guide", "priority": "0.7"},
        {"loc": "/pdf-accessibility-guide", "priority": "0.7"},
        {"loc": "/about", "priority": "0.5"},
        {"loc": "/privacy", "priority": "0.3"},
        {"loc": "/terms", "priority": "0.3"},
        {"loc": "/contact", "priority": "0.5"}
    ]
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    base_url = "https://freepdftools.carbonprojects.dev"
    
    for page in pages:
        xml_content += '  <url>\n'
        xml_content += f'    <loc>{base_url}{page["loc"]}</loc>\n'
        xml_content += '    <lastmod>2025-04-01</lastmod>\n'
        xml_content += '    <changefreq>monthly</changefreq>\n'
        xml_content += f'    <priority>{page["priority"]}</priority>\n'
        xml_content += '  </url>\n'
    
    xml_content += '</urlset>'
    
    return xml_content, 200, {'Content-Type': 'application/xml'}


# Generate robots.txt
@app_routes.route("/robots.txt")
def robots():
    """Generate a robots.txt file."""
    return """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /internal/

Sitemap: https://freepdftools.carbonprojects.dev/sitemap.xml
""", 200, {'Content-Type': 'text/plain'}


@app_routes.route("/ads.txt")
def ads_txt():
    return """google.com, pub-7978428607757975, DIRECT, f08c47fec0942fa0""", 200, {'Content-Type': 'text/plain'}

@app_routes.route("/admin/messages", methods=["GET"])
def admin_messages():

    admin_key = os.environ.get('ADMIN_KEY', 'default-key-for-development')

    if request.args.get('key') != admin_key:
        return "Unauthorized", 401

        
    messages_dir = "/app/messages"
    messages = []
    
    # Make sure the directory exists
    if not os.path.exists(messages_dir):
        return render_template("admin_messages.html", messages=[], message_count=0)
    
    # Get all message files
    for filename in os.listdir(messages_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(messages_dir, filename)
            try:
                with open(file_path, 'r') as f:
                    message_data = json.load(f)
                    # Add filename to message data for deletion reference
                    message_data['filename'] = filename
                    messages.append(message_data)
            except:
                continue
    
    # Sort messages by timestamp (newest first)
    messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return render_template("admin_messages.html", messages=messages, message_count=len(messages))

@app_routes.route("/admin/messages/delete", methods=["GET"])
def delete_message():

    admin_key = os.environ.get('ADMIN_KEY', 'default-key-for-development')

    # Simple authentication with a secret key in the URL
    if request.args.get('key') != admin_key:
        return "Unauthorized", 401
    
    filename = request.args.get('filename')
    if not filename:
        return "No filename specified", 400
    
    # Make sure the filename is safe (no path traversal)
    filename = os.path.basename(filename)
    
    file_path = os.path.join("/app/messages", filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return redirect(f"/admin/messages?key={request.args.get('key')}&deleted=true")
    else:
        return "File not found", 404
    

@app_routes.route("/split-pdf", methods=["GET", "POST"])
def split_pdf():
    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return render_template("split.html", error="No file selected")

            filename = secure_filename(file.filename)
            upload_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(upload_path)

            # Read the uploaded PDF
            pdf_reader = PdfReader(upload_path)
            total_pages = len(pdf_reader.pages)

            return render_template("split.html", uploaded_file=filename, total_pages=total_pages)

        elif "filename" in request.form:
            filename = request.form.get("filename")
            selected_pages = request.form.getlist("pages")

            if not selected_pages:
                return render_template("split.html", error="No pages selected")

            input_path = os.path.join(UPLOAD_FOLDER, filename)
            zip_filename = f"selected_pages_{os.path.splitext(filename)[0]}.zip"
            zip_path = os.path.join(UPLOAD_FOLDER, zip_filename)

            pdf_reader = PdfReader(input_path)

            with zipfile.ZipFile(zip_path, "w") as zipf:
                for page_num in selected_pages:
                    page_index = int(page_num) - 1
                    if 0 <= page_index < len(pdf_reader.pages):
                        writer = PdfWriter()
                        writer.add_page(pdf_reader.pages[page_index])

                        page_filename = f"page_{page_num}.pdf"
                        page_path = os.path.join(UPLOAD_FOLDER, page_filename)

                        with open(page_path, "wb") as f:
                            writer.write(f)
                        zipf.write(page_path, arcname=page_filename)
                        os.remove(page_path)

            return render_template("split.html", success=True, download_link=f"/download?filename={zip_filename}")

    return render_template("split.html")
