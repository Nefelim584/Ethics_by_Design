import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for
from flask_cors import CORS
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import Transcript, User, get_session, init_db
from transcription import get_client, transcribe_file

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR / "static"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

CORS(
    app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": "http://localhost:5173"}},
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "page_login"

oauth = OAuth(app)
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@login_manager.user_loader
def load_user(user_id: str):
    with get_session() as db:
        return db.get(User, int(user_id))


# ── HTML page routes ────────────────────────────────────────────
@app.get("/")
def index():
    if current_user.is_authenticated:
        return send_from_directory(FRONTEND_DIR, "main.html")
    return redirect(url_for("page_login"))


@app.get("/login")
def page_login():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.get("/register")
def page_register():
    return send_from_directory(FRONTEND_DIR, "register.html")


# ── Email / password auth ───────────────────────────────────────
@app.post("/auth/register")
def auth_register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    with get_session() as db:
        existing = db.query(User).filter_by(email=email).one_or_none()
        if existing:
            return jsonify({"error": "An account with this email already exists"}), 409

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=email.split("@")[0],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    login_user(user)
    session.permanent = True
    return jsonify({"ok": True, "email": user.email}), 201


@app.post("/auth/login")
def auth_login_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with get_session() as db:
        user = db.query(User).filter_by(email=email).one_or_none()
        if user is None or not user.password_hash or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)
    session.permanent = True
    return jsonify({"ok": True, "email": user.email})


# ── Google OAuth ────────────────────────────────────────────────
@app.get("/auth/login/google")
def auth_login_google():
    redirect_uri = url_for("auth_callback_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.get("/auth/callback/google")
def auth_callback_google():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        return redirect(url_for("page_login") + "?error=auth_failed")

    email = user_info.get("email")
    name = user_info.get("name")

    with get_session() as db:
        user = db.query(User).filter_by(email=email).one_or_none()
        if user is None:
            user = User(email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)

    login_user(user)
    session.permanent = True
    return redirect(url_for("index"))


@app.post("/auth/logout")
@login_required
def auth_logout():
    logout_user()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 401
    return jsonify(
        {
            "authenticated": True,
            "email": current_user.email,
            "name": current_user.name,
        }
    )


@app.post("/api/transcribe")
@login_required
def api_transcribe():
    if "file" not in request.files:
        return jsonify({"error": "Missing 'file' field in multipart form-data"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    model = request.form.get("model", "voxtral-mini-latest")
    language = request.form.get("language") or None
    num_speakers = request.form.get("num_speakers") or None
    prompt = request.form.get("prompt") or None
    output_format = request.form.get("output_format", "txt")

    if num_speakers is not None:
        try:
            num_speakers = int(num_speakers)
        except (ValueError, TypeError):
            num_speakers = None

    with NamedTemporaryFile(delete=True, suffix=Path(file.filename).suffix) as tmp:
        file.save(tmp.name)
        audio_path = Path(tmp.name)

        client = get_client()
        text = transcribe_file(
            client=client,
            audio_path=audio_path,
            model=model,
            language=language,
            num_speakers=num_speakers,
            prompt=prompt,
            output_format=output_format,
        )

    with get_session() as db:
        transcript = Transcript(
            user_id=current_user.id,
            file_name=file.filename,
            model=model,
            language=language,
            text=text,
        )
        db.add(transcript)
        db.commit()

    return jsonify(
        {
            "model": model,
            "language": language,
            "text": text,
        }
    )


@app.get("/api/transcripts")
@login_required
def api_transcripts():
    with get_session() as db:
        rows = (
            db.query(Transcript)
            .filter_by(user_id=current_user.id)
            .order_by(Transcript.created_at.desc())
            .all()
        )
        return jsonify(
            [
                {
                    "id": t.id,
                    "file_name": t.file_name,
                    "model": t.model,
                    "language": t.language,
                    "created_at": t.created_at.isoformat(),
                }
                for t in rows
            ]
        )


@app.get("/api/transcripts/<int:transcript_id>")
@login_required
def api_transcript_detail(transcript_id: int):
    with get_session() as db:
        t = (
            db.query(Transcript)
            .filter_by(user_id=current_user.id, id=transcript_id)
            .one_or_none()
        )
        if t is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(
            {
                "id": t.id,
                "file_name": t.file_name,
                "model": t.model,
                "language": t.language,
                "created_at": t.created_at.isoformat(),
                "text": t.text,
            }
        )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5841, debug=True)

