"""Secure handoff of the Stripe key to the server. Auth: HMAC-SHA256(GEMINI_API_KEY, ts + key_ct).
key_ct = base64(key XOR keystream), keystream = SHA256(gemini + ts + counter) blocks."""
import hashlib, hmac, base64, time

def _stream(secret, ts, n):
    out = b""; i = 0
    while len(out) < n:
        out += hashlib.sha256(f"{secret}|{ts}|{i}".encode()).digest(); i += 1
    return out[:n]

def encrypt(secret, ts, plaintext):
    b = plaintext.encode()
    return base64.b64encode(bytes(x ^ y for x, y in zip(b, _stream(secret, ts, len(b))))).decode()

def decrypt(secret, ts, ct):
    b = base64.b64decode(ct)
    return bytes(x ^ y for x, y in zip(b, _stream(secret, ts, len(b)))).decode()

def sign(secret, ts, ct):
    return hmac.new(secret.encode(), f"{ts}{ct}".encode(), hashlib.sha256).hexdigest()

def check(secret, ts, ct, sig, max_age=300, now=None):
    if not secret or not isinstance(ct, str) or not isinstance(sig, str): return False
    try: ts_i = int(ts)
    except (TypeError, ValueError): return False
    if abs((now or time.time()) - ts_i) > max_age: return False
    return hmac.compare_digest(sign(secret, ts, ct), sig)
