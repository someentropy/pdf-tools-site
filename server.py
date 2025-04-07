from app import create_app
from flask import request, redirect

app = create_app()

# 301 redirect for old domain to new domain
@app.before_request
def redirect_to_new_domain():
    if request.host == "freepdftools.fly.dev":
        return redirect(f"https://freepdftools.carbonprojects.dev{request.full_path}", code=301)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
