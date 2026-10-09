# project-locker

Password-based file encryption, with a command-line tool and a desktop GUI.

## How it works

- `locker.py` holds the encryption logic and the CLI.
  - A 256-bit key is derived from the password with scrypt (`n=2**17, r=8, p=1`) and a random 16-byte salt.
  - The file is encrypted with AES-256-GCM using a random 12-byte nonce. GCM authenticates the data, so a wrong password or a tampered file is rejected instead of producing garbage.
  - Output is written to `<file>.locked` as `LOCK1 | salt | nonce | ciphertext`. The `LOCK1` magic is passed as associated data, so it is authenticated too.
  - Decrypting strips `.locked` and restores the original file, neither encrypting/decrypting overwrites an existing file.
- `locker_gui.py` is a Tkinter front end styled with a Windows XP like style design system. It reads the file header to decide whether to encrypt or decrypt, and runs the work in a background thread so the window stays responsive.

## Setup

Requires Python 3.9+.

```
python -m venv .venv
.venv\Scripts\activate
pip install cryptography
```

## Usage

GUI:

```
python locker_gui.py
```

Pick a file with Browse, enter a password (and confirm it when encrypting), then click Encrypt or Decrypt. Results appear in the log on the right.

CLI:

```
python locker.py encrypt secret.txt
python locker.py decrypt secret.txt.locked
```