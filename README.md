
<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
</p>

<h1 align="center">◉ Cerberus</h1>

<p align="center">
  A web application for encrypting video files using AES-256-CBC and converting encrypted data into Morse code.<br>
  Both the Morse code and encrypted text can be decoded back into the original video.
</p>

---

## ✦ Features

- 🔐 **AES-256-CBC Encryption:** Password-based encryption with PBKDF2 key derivation using 200,000 iterations.
- ◉ **Morse Code Conversion:** Custom Morse dictionary supporting all 95 printable ASCII characters.
- 📦 **Dual Output:** Each encryption generates two downloadable files:
  - `*_encrypted.txt` (Base64 ciphertext, approximately 1.33× the original file size)
  - `*_morse.txt` (Morse code representation)
- 🔄 **Flexible Decoding:** Restore the original video from either file type with automatic detection.
- ✅ **Startup Verification:** Runs a round-trip encryption and decryption test on startup.
- 🎞️ **Supported Formats:** MP4, MOV, AVI, MKV, WebM, FLV and WMV, with a file size limit of 500 MB.

---

## ✦ Quick Start

**Prerequisites:** Python 3.10 or above.

### 1. Clone the Repository

```bash
git clone https://github.com/g34rh3ad/Cerberus.git
cd Cerberus
```

### 2. Environment Setup

#### macOS & Linux

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

#### Windows

```cmd
:: Create a virtual environment
python -m venv venv

:: Activate using Command Prompt
venv\Scripts\activate

:: For PowerShell, use:
:: .\venv\Scripts\Activate.ps1

:: Install dependencies
pip install -r requirements.txt

:: Run the application
python app.py
```

Once the application is running, open **http://localhost:5002** in your browser.

---

## ✦ How to Use

### Encode (Video → Encrypted + Morse)

1. Open the **Encode** tab.
2. Drag and drop a video or select one from your device.
3. Enter a password of at least 8 characters.
4. Click **Encrypt Video**.
5. Download the encrypted text file, Morse code file or both.

### Decode (Morse / Encrypted → Video)

1. Open the **Decode** tab.
2. Select **Morse File** or **Encrypted File**.
3. Upload the corresponding `.txt` file.
4. Enter the password used during encryption.
5. Select the output format and click **Decrypt → Video**.

---

## ✦ Project Structure

```
Cerberus/
│
├── app.py                 # Flask backend, encryption, Morse logic and routes
├── templates/
│   └── index.html         # User interface, styles and JavaScript
│
├── requirements.txt       # Python dependencies
├── .gitignore
├── uploads/               # Temporary uploaded files (gitignored)
├── outputs/               # Generated output files (gitignored)
└── morse.db               # SQLite Morse dictionary, rebuilt on startup
```

---

## ✦ API

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/` | Main web interface |
| `POST` | `/encode` | Encrypt a video and generate Morse code |
| `POST` | `/decode` | Restore a video from Morse code or encrypted text |
| `GET` | `/download/<file>` | Download a generated file |
| `GET` | `/morse-table` | Retrieve the Morse dictionary as JSON |

---

## ✦ How It Works

### Encryption Pipeline

```
Video bytes
  → PKCS7 padding
  → AES-256-CBC encryption
  → Base64 encoding
  → Morse code conversion
```

A random 16-byte salt and 16-byte initialization vector (IV) are generated for each encryption.

The password is used to derive a 256-bit encryption key through PBKDF2-HMAC-SHA256 with 200,000 iterations.

The salt, IV and ciphertext are stored together in the following format:

```
salt ‖ IV ‖ ciphertext
```

The combined data is encoded into Base64 and then converted into Morse code using the custom ASCII dictionary.

### Decryption Pipeline

```
Morse code or Base64
  → Base64 decoding
  → Extract salt, IV and ciphertext
  → AES-256-CBC decryption
  → Remove PKCS7 padding
  → Original video
```

Decryption reverses the encryption process using the original password. If the input is a Morse code file, it is first converted back into Base64.

Morse code is used as an additional encoding format, not as a separate layer of encryption.

---

## ✦ Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python, Flask |
| Cryptography | `cryptography` (AES-256-CBC, PBKDF2) |
| Database | SQLite |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Fonts | Inter, JetBrains Mono |

---

## ✦ License

This project is licensed under the MIT License and is available for personal and commercial use, subject to the license terms.
