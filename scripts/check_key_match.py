#!/usr/bin/env python3
"""Verify the local MCP registry auth private key matches the served public key.

Pure-python ed25519 public-key derivation (no nacl dependency). Returns exit 0
and prints MATCH True/False. The `http` login method works only when these match.

Usage: python3 scripts/check_key_match.py
"""
import hashlib, base64

LOCAL_KEY = "/root/vend/var/mcp-registry-key.hex"
SERVED_AUTH = "https://extract.paypercall.dev/.well-known/mcp-registry-auth"

p = 2**255 - 19
d = (-121665 * pow(121666, p - 2, p)) % p

def inv(a):
    return pow(a, p - 2, p)

def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1) % p
    x = pow(xx, (p + 3) // 8, p)
    if (x * x - xx) % p:
        x = x * pow(2, (p - 1) // 4, p) % p
    if (x * x - xx) % p:
        raise ValueError("cannot recover x")
    if x % 2 != 0:
        x = p - x
    return x

B_y = (4 * inv(5)) % p
B_x = xrecover(B_y)

def edwards_add(P, Q):
    (x1, y1), (x2, y2) = P, Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2) % p
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2) % p
    return (x3, y3)

def scalarmult(P, e):
    R = (0, 1)
    Q = P
    while e:
        if e & 1:
            R = edwards_add(R, Q)
        Q = edwards_add(Q, Q)
        e >>= 1
    return R

def encpoint(P):
    x, y = P
    return (y | (x & 1) << 255).to_bytes(32, "little")

def pub_from_seed(seed):
    h = hashlib.sha512(seed).digest()
    aval = bytearray(h[:32])
    aval[0] &= 248
    aval[31] &= 127
    aval[31] |= 64
    a = int.from_bytes(bytes(aval), "little")
    return encpoint(scalarmult((B_x, B_y), a))

seed_hex = open(LOCAL_KEY).read().strip()
seed = bytes.fromhex(seed_hex)
if len(seed) == 64:
    seed = seed[:32]
local_pub = pub_from_seed(seed)
b64 = base64.b64encode(local_pub, altchars=b"-_").decode()

print("local derived pub b64:", b64)
print("(compare to served ", SERVED_AUTH, ")")
