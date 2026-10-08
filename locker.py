import argparse
import getpass
import os
import sys

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"LOCK1"
SALT_LEN = 16
NONCE_LEN = 12
EXT = ".locked"

def derive_key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(password.encode())

def encrypt_file(path: str, password: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    # magic passed as associated data: auth'ed but not encrypted
    ciphertext = AESGCM(derive_key(password, salt)).encrypt(nonce, data, MAGIC)
    out = path + EXT
    with open(out, "xb") as f: 
    # "x" refuses to overwrite file
        f.write(MAGIC + salt + nonce + ciphertext)
    return out

def decrypt_file(path: str, password: str) -> str:
    with open(path, "rb") as f:
        blob = f.read()
    if not blob.startswith(MAGIC):
        sys.exit("Not locked file")
    i = len(MAGIC)
    salt = blob[i:i + SALT_LEN]
    nonce = blob[i + SALT_LEN:i + SALT_LEN + NONCE_LEN]
    ciphertext = blob[i + SALT_LEN + NONCE_LEN:]
    try:
        data = AESGCM(derive_key(password, salt)).decrypt(nonce, ciphertext, MAGIC)
    except InvalidTag:
        sys.exit("Wrong password or file has been tampered with")
    out = path.removesuffix(EXT)
    with open(out, "xb") as f:
        f.write(data)
    return out

def main():
    parser = argparse.ArgumentParser(description="Password-based file encryption")
    parser.add_argument("mode", choices=["encrypt", "decrypt"])
    parser.add_argument("file")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    try:
        if args.mode == "encrypt":
            if password != getpass.getpass("Confirm: "):
                sys.exit("Passwords don't match.")
            print("Wrote", encrypt_file(args.file, password))
        else:
            print("Wrote", decrypt_file(args.file, password))
    except FileExistsError as e:
        sys.exit(f"Output file already exists: {e.filename}")
    except FileNotFoundError as e:
        sys.exit(f"File not found: {e.filename}")


if __name__ == "__main__":
    main()