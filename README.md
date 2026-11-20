<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/encryption-AES--256--CBC-292524?style=for-the-badge&logo=letsencrypt&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
</p>

<h1 align="center">◉ Cerberus</h1>

<p align="center">
  Encrypt video files with AES-256-CBC and convert the ciphertext into Morse code.<br>
  Decode Morse code or encrypted text back into the original video.
</p>

---

## ✦ Features

- 🔐 **AES-256-CBC Encryption** — Password-based encryption using PBKDF2 key derivation (200K iterations)
- ◉ **Morse Code Conversion** — Custom dictionary covering all 95 printable ASCII characters
- 📦 **Dual Output** — Every encode produces two downloadable files:
  - `*_encrypted.txt` — Compact Base64 ciphertext (~1.3× original size)
  - `*_morse.txt` — Dots-and-dashes representation
- 🔄 **Flexible Decoding** — Restore videos from either file type with auto-detection
- ✅ **Startup Verification** — Full roundtrip test runs on every launch
- 🎞️ **7 Formats** — MP4, MOV, AVI, MKV, WebM, FLV, WMV (up to 500 MB)

---

## ✦ Quick Start

> **Prerequisites:** Python 3.10+

### 1. Clone the Repository

```bash
git clone https://github.com/g34rh3ad/Cerberus.git
cd Cerberus
```

### 2. Environment Setup

#### MacOS & Linux
```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

#### Windows
```cmd
:: Create a virtual environment
python -m venv venv

:: Activate the virtual environment (Command Prompt)
venv\Scripts\activate

:: OR Activate the virtual environment (PowerShell)
:: .\venv\Scripts\Activate.ps1

:: Install dependencies
pip install -r requirements.txt

:: Run the app
python app.py
```

---

Open **http://localhost:5002** in your web browser.

---

## ✦ How to Use

### Encode (Video → Encrypted + Morse)

1. Go to the **Encode** tab
2. Drop or select a video file
3. Enter a password (min 8 characters)
4. Click **Encrypt Video**
5. Download the encrypted `.txt` and/or Morse `.txt`

### Decode (Morse / Encrypted → Video)

1. Go to the **Decode** tab
2. Pick **Morse File** or **Encrypted File**
3. Upload the `.txt` file
4. Enter the same password
5. Select output format → Click **Decrypt → Video**

---

## ✦ Project Structure

```
Cerberus/
│
├── app.py                 # Flask backend — crypto, Morse engine, routes
├── templates/
│   └── index.html         # Single-page UI — styles, layout, client JS
│
├── requirements.txt       # Python dependencies
├── .gitignore
├── uploads/               # Temp upload storage (gitignored)
├── outputs/               # Generated download files (gitignored)
└── morse.db               # SQLite Morse dictionary (rebuilt on startup)
```

---

## ✦ API

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/` | Web UI |
| `POST` | `/encode` | Encrypt video + generate Morse |
| `POST` | `/decode` | Decode Morse or encrypted text → video |
| `GET` | `/download/<file>` | Download generated file |
| `GET` | `/morse-table` | Full Morse dictionary (JSON) |

---

## ✦ How It Works

### Encryption Pipeline

```
Video bytes
  → PKCS7 pad
  → AES-256-CBC encrypt (random salt + IV)
  → Base64 encode
  → Morse encode
```

- A random **16-byte salt** and **16-byte IV** are generated per encryption
- Password → 256-bit key via **PBKDF2-HMAC-SHA256** (200,000 iterations)
- Output blob: `salt ‖ IV ‖ ciphertext` → Base64 string → Morse string


## ✦ Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python, Flask |
| Crypto | `cryptography` (AES-256-CBC, PBKDF2) |
| Database | SQLite  |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Fonts | Inter, JetBrains Mono |

---

## ✦ License

MIT — free for personal and commercial use.
