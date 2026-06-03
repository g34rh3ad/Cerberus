import os
import re
import hashlib
import base64
import sqlite3
from typing import Optional

from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
DB_PATH = os.path.join(BASE_DIR, "morse.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "flv", "wmv"}

PBKDF2_ITERATIONS = 200_000
SALT_SIZE = 16
IV_SIZE   = 16
KEY_SIZE  = 32


_MORSE:  dict = {}
_RMORSE: dict = {}


def _build_morse_pairs() -> list:
    char_groups = [
        ('=+/#0123',                                                3),

        ('456789ABCDEFGHIJ',                                        4),

        ('KLMNOPQRSTUVWXYZ' + 'abcdefghijklmnop',                   5),

        ('qrstuvwxyz'
         ' !"$%&\'()*,-.:;<>?@[\\]^_`{|}~',
                                                                    6),
    ]
    pairs = []
    for chars, length in char_groups:
        for idx, ch in enumerate(chars):
            code = ''.join(
                '.' if not ((idx >> (length - 1 - j)) & 1) else '-'
                for j in range(length)
            )
            pairs.append((ch, code))
    return pairs


def _init_morse_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS morse_codes")
    conn.execute('''
        CREATE TABLE morse_codes (
            character TEXT PRIMARY KEY,
            code      TEXT UNIQUE NOT NULL
        )
    ''')
    pairs = _build_morse_pairs()
    conn.executemany("INSERT INTO morse_codes VALUES(?,?)", pairs)
    conn.commit()
    conn.close()
    return pairs


def _load_morse_caches():
    global _MORSE, _RMORSE
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT character, code FROM morse_codes").fetchall()
    _MORSE  = {r['character']: r['code'] for r in rows}
    _RMORSE = {r['code']: r['character'] for r in rows}
    conn.close()


def morse_enc(text: str) -> str:
    if not _MORSE:
        _load_morse_caches()
    return ' '.join(_MORSE.get(ch, '?') for ch in text)


def morse_dec(morse: str) -> str:
    if not _RMORSE:
        _load_morse_caches()
    return ''.join(_RMORSE.get(tok, '?') for tok in morse.strip().split(' '))


def is_morse_content(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    return bool(re.fullmatch(r'[.\- \n\r]+', cleaned))


def sanitize_morse(raw: str) -> str:
    cleaned = re.sub(r'[^.\- ]', ' ', raw)
    cleaned = re.sub(r' {2,}', ' ', cleaned).strip()
    return cleaned


def derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_SIZE,
    )


def encrypt_video(video_bytes: bytes, password: str) -> str:
    salt = os.urandom(SALT_SIZE)
    iv   = os.urandom(IV_SIZE)
    key  = derive_key(password, salt)

    padder      = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(video_bytes) + padder.finalize()

    cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    encrypted_blob = salt + iv + ciphertext
    return base64.b64encode(encrypted_blob).decode("utf-8")


def decrypt_video(encrypted_text: str, password: str) -> bytes:
    try:
        encrypted_blob = base64.b64decode(encrypted_text)
    except Exception:
        raise ValueError("Invalid encrypted text — the data may be corrupted or "
                         "you may have uploaded a Morse file instead of an "
                         "encrypted file.")

    if len(encrypted_blob) < SALT_SIZE + IV_SIZE + 16:
        raise ValueError("Encrypted data is too short — this may not be a valid "
                         "encrypted file. If you have a Morse file, use the "
                         "'From Morse File' option instead.")

    salt       = encrypted_blob[:SALT_SIZE]
    iv         = encrypted_blob[SALT_SIZE : SALT_SIZE + IV_SIZE]
    ciphertext = encrypted_blob[SALT_SIZE + IV_SIZE :]
    key        = derive_key(password, salt)

    cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    try:
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception:
        raise ValueError("Wrong password or corrupted file.")

    try:
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
    except Exception:
        raise ValueError("Wrong password or corrupted file.")

    return data


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/encode", methods=["POST"])
def encode_route():
    if "video" not in request.files:
        return jsonify({"error": "No video file uploaded."}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        exts = ', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return jsonify({"error": f"Unsupported format. Allowed: {exts}"}), 400

    password = request.form.get("password", "")
    pw_error = validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    video_bytes = file.read()
    if len(video_bytes) > MAX_FILE_SIZE_BYTES:
        return jsonify({"error": f"File too large. Maximum: {MAX_FILE_SIZE_MB} MB."}), 400
    if len(video_bytes) == 0:
        return jsonify({"error": "Uploaded file is empty."}), 400

    original_size = len(video_bytes)

    try:
        encrypted_text = encrypt_video(video_bytes, password)
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {str(e)}"}), 500

    del video_bytes

    encrypted_size = len(encrypted_text)

    try:
        morse_text = morse_enc(encrypted_text)
    except Exception as e:
        return jsonify({"error": f"Morse conversion failed: {str(e)}"}), 500

    morse_size = len(morse_text)

    original_name = secure_filename(file.filename)
    base_name     = os.path.splitext(original_name)[0]

    enc_name = f"{base_name}_encrypted.txt"
    enc_path = os.path.join(OUTPUT_FOLDER, enc_name)
    with open(enc_path, "w", encoding="utf-8") as f:
        f.write(encrypted_text)

    morse_name = f"{base_name}_morse.txt"
    morse_path = os.path.join(OUTPUT_FOLDER, morse_name)
    with open(morse_path, "w", encoding="utf-8") as f:
        f.write(morse_text)

    PREVIEW_LEN = 500
    MORSE_PREVIEW_LEN = 3000

    return jsonify({
        "ok": True,
        "preview": encrypted_text[:PREVIEW_LEN],
        "total_chars": encrypted_size,
        "morse_preview": morse_text[:MORSE_PREVIEW_LEN],
        "morse_total_chars": morse_size,
        "stats": {
            "original_size":  format_size(original_size),
            "encrypted_size": format_size(encrypted_size),
            "morse_size":     format_size(morse_size),
        },
        "downloads": {
            "encrypted_file": enc_name,
            "morse_file":     morse_name,
        },
    })


@app.route("/decode", methods=["POST"])
def decode_route():
    password = request.form.get("password", "")
    pw_error = validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    video_ext = request.form.get("video_ext", "mp4").lower().strip(".")
    if video_ext not in ALLOWED_VIDEO_EXTENSIONS:
        exts = ', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return jsonify({"error": f"Unsupported output format. Allowed: {exts}"}), 400

    input_mode     = request.form.get("input_mode", "file")
    encrypted_text = ""

    if input_mode == "morse":
        morse_input = request.form.get("morse_code", "").strip()
        if not morse_input:
            return jsonify({"error": "No Morse code provided."}), 400
        morse_input = sanitize_morse(morse_input)
        if not morse_input:
            return jsonify({"error": "No valid Morse code found in input."}), 400
        try:
            encrypted_text = morse_dec(morse_input)
        except Exception as e:
            return jsonify({"error": f"Morse decoding failed: {str(e)}"}), 400
        if '?' in encrypted_text:
            return jsonify({
                "error": "Morse code appears incomplete or corrupted. "
                         "Make sure you paste the complete Morse code, "
                         "not a truncated preview."
            }), 400

    elif input_mode == "morse_file":
        if "encrypted_file" not in request.files:
            return jsonify({"error": "No Morse file uploaded."}), 400
        file = request.files["encrypted_file"]
        if file.filename == "":
            return jsonify({"error": "No file selected."}), 400
        raw = file.read().decode("utf-8", errors="replace").strip()
        if not raw:
            return jsonify({"error": "Uploaded file is empty."}), 400
        morse_input = sanitize_morse(raw)
        if not morse_input:
            return jsonify({"error": "File does not contain valid Morse code."}), 400
        try:
            encrypted_text = morse_dec(morse_input)
        except Exception as e:
            return jsonify({"error": f"Morse decoding failed: {str(e)}"}), 400
        if '?' in encrypted_text:
            return jsonify({
                "error": "Morse file contains unrecognized codes. "
                         "It may be corrupted or incomplete."
            }), 400

    else:
        if "encrypted_file" not in request.files:
            return jsonify({"error": "No encrypted file uploaded."}), 400
        file = request.files["encrypted_file"]
        if file.filename == "":
            return jsonify({"error": "No file selected."}), 400
        raw = file.read().decode("utf-8", errors="replace").strip()
        if not raw:
            return jsonify({"error": "Uploaded file is empty."}), 400

        if is_morse_content(raw):
            morse_input = sanitize_morse(raw)
            try:
                encrypted_text = morse_dec(morse_input)
            except Exception as e:
                return jsonify({"error": f"Morse decoding failed: {str(e)}"}), 400
            if '?' in encrypted_text:
                return jsonify({
                    "error": "This looks like a Morse file but contains "
                             "unrecognized codes. It may be corrupted."
                }), 400
        else:
            encrypted_text = raw

    try:
        video_bytes = decrypt_video(encrypted_text.strip(), password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Decryption failed: {str(e)}"}), 500

    output_name = f"restored_video.{video_ext}"
    output_path = os.path.join(OUTPUT_FOLDER, output_name)
    with open(output_path, "wb") as f:
        f.write(video_bytes)

    mime_map = {
        "mp4": "video/mp4",       "mov": "video/quicktime",
        "avi": "video/x-msvideo", "mkv": "video/x-matroska",
        "webm": "video/webm",     "flv": "video/x-flv",
        "wmv": "video/x-ms-wmv",
    }
    return send_file(
        output_path,
        as_attachment=True,
        download_name=output_name,
        mimetype=mime_map.get(video_ext, "application/octet-stream"),
    )


@app.route("/download/<filename>")
def download_file(filename):
    safe = secure_filename(filename)
    path = os.path.join(OUTPUT_FOLDER, safe)
    if not os.path.exists(path):
        return jsonify({"error": "File not found."}), 404
    return send_file(path, as_attachment=True, download_name=safe,
                     mimetype="text/plain")


@app.route("/morse-table")
def morse_table():
    if not _MORSE:
        _load_morse_caches()
    groups = {}
    for char, code in sorted(_MORSE.items(), key=lambda x: (len(x[1]), x[1])):
        length = len(code)
        groups.setdefault(length, []).append({"char": char, "code": code})
    return jsonify({
        "total":  len(_MORSE),
        "groups": groups,
        "all":    [{"char": ch, "code": co}
                   for ch, co in sorted(_MORSE.items(),
                                         key=lambda x: (len(x[1]), x[1]))],
    })


if __name__ == "__main__":
    pairs = _init_morse_db()
    _load_morse_caches()

    b64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    missing = [c for c in b64_chars if c not in _MORSE]
    if missing:
        print(f"  ❌  FATAL: Missing Morse codes for: {missing}")
        exit(1)

    import string
    test_data = b"ROUNDTRIP_TEST_DATA_1234567890"
    test_pw   = "verifytest"
    enc_text  = encrypt_video(test_data, test_pw)
    enc_morse = morse_enc(enc_text)
    dec_text  = morse_dec(enc_morse)
    dec_data  = decrypt_video(dec_text, test_pw)
    assert dec_data == test_data, "Roundtrip verification FAILED!"
    assert dec_text == enc_text,  "Morse roundtrip FAILED!"

    print("=" * 58)
    print("  🔐  Video-Morse Encryptor")
    print("  🌐  Open in browser: http://localhost:5002")
    print("=" * 58)
    app.run(debug=False, host="0.0.0.0", port=5002)
