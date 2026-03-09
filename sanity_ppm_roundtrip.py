#!/usr/bin/env python3
# sanity_ppm_roundtrip.py (versão verbosa + entropia)
# Mostra entrada, bytes comprimidos (em hex), saída da descompressão e métricas:
# - razão, ganho %, BPC, entropia H0 (bits/char), gap p/ ideal.

import argparse
import os
import sys
import time
import math
from collections import Counter

try:
    from ppm_compressor import PPMCompressor
except Exception as e:
    print("Erro ao importar PPMCompressor de ppm_compressor.py:", e, file=sys.stderr)
    sys.exit(2)

def _unwrap_compress(compressor, data: bytes):
    t0 = time.perf_counter()
    out = compressor.compress(data)
    t1 = time.perf_counter()
    if isinstance(out, tuple):
        comp, stats = out
        t_comp_ms = stats.get("compression_time", (t1 - t0)) * 1000.0
    else:
        comp, stats = out, None
        t_comp_ms = (t1 - t0) * 1000.0
    return comp, stats, t_comp_ms

def _unwrap_decompress(compressor, comp: bytes, n: int):
    t0 = time.perf_counter()
    out = compressor.decompress(comp, n)
    t1 = time.perf_counter()
    if isinstance(out, tuple):
        decomp, stats = out
        t_decomp_ms = stats.get("decompression_time", (t1 - t0)) * 1000.0
    else:
        decomp, stats = out, None
        t_decomp_ms = (t1 - t0) * 1000.0
    return decomp, stats, t_decomp_ms

def b2hex(b: bytes, sep: str = " "):
    return sep.join(f"{x:02x}" for x in b)

def safe_str(b: bytes):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return b.decode("latin-1")
        except Exception:
            return repr(b)

def entropy_zero_order_bits_per_char(data: bytes) -> float:
    """Entropia empírica H0 em bits/char (ordem 0)."""
    n = len(data)
    if n == 0:
        return 0.0
    counts = Counter(data)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h  # bits por símbolo

def show_case(label: str, k: int, msg: bytes, verbose: bool = True):
    n = len(msg)
    c1 = PPMCompressor(k)
    comp, cstats, tcomp = _unwrap_compress(c1, msg)

    c2 = PPMCompressor(k)  # decoder novo/limpo
    decomp, dstats, tdecomp = _unwrap_decompress(c2, comp, len(msg))

    ok = (msg == decomp)
    ratio = (len(comp) / n) if n else 0.0
    gain_pct = (1.0 - ratio) * 100.0 if n else 0.0
    bpc = (8.0 * len(comp) / n) if n else 0.0

    # Entropia de ordem 0 (bits/char) e “ideal” em bytes
    H0 = entropy_zero_order_bits_per_char(msg)
    ideal_bytes = (H0 * n) / 8.0  # limite Shannon para ordem 0
    gap_bits_per_char = bpc - H0
    over_entropy_pct = ( (len(comp) - ideal_bytes) / ideal_bytes * 100.0 ) if ideal_bytes > 0 else float('inf')

    if verbose:
        print("=" * 88)
        print(f"[{label}]  K={k}")
        print("- Entrada -------------------------------")
        print(f"bytes  ({len(msg)}): {msg!r}")
        print(f"string       : {safe_str(msg)}")
        print("- Comprimido ----------------------------")
        print(f"bytes  ({len(comp)}): {comp!r}")
        print(f"hex          : {b2hex(comp)}")
        print("- Descompressão -------------------------")
        print(f"bytes  ({len(decomp)}): {decomp!r}")
        print(f"string       : {safe_str(decomp)}")
        print("- Métricas ------------------------------")
        print(f"ratio        : {ratio:.4f}")
        print(f"ganho        : {gain_pct:.2f}%")
        print(f"BPC          : {bpc:.3f} bits/char")
        print(f"H0 (ordem 0) : {H0:.3f} bits/char")
        print(f"gap (BPC-H0) : {gap_bits_per_char:.3f} bits/char")
        print(f"acima do ideal(H0) ~ {over_entropy_pct:.1f}%")
        print(f"t_comp       : {tcomp:.2f} ms")
        print(f"t_decomp     : {tdecomp:.2f} ms")
        print(f"round-trip ok: {ok}")
        print("=" * 88)
        print()

    return {
        "ok": ok,
        "out_len": len(comp),
        "ratio": ratio,
        "gain_pct": gain_pct,
        "bpc": bpc,
        "H0": H0,
        "gap_bpc_h0": gap_bits_per_char,
        "over_entropy_pct": over_entropy_pct,
        "tcomp_ms": tcomp,
        "tdecomp_ms": tdecomp,
    }

def main():
    parser = argparse.ArgumentParser(description="Sanity round-trip tests verbosos para PPM-C (com entropia)")
    parser.add_argument("--ks", default="2", help="Lista de ordens K separadas por vírgula (ex.: 0,1,2,3) [default: 2]")
    parser.add_argument("--random", type=int, default=0, help="Quantos casos aleatórios adicionais [default: 0]")
    parser.add_argument("--rand-bytes", type=int, default=4096, help="Tamanho do payload aleatório [default: 4096]")
    parser.add_argument("--no-verbose", dest="no_verbose", action="store_true",
                        help="Não imprimir blocos detalhados por caso")
    args = parser.parse_args()

    try:
        ks = [int(x.strip()) for x in args.ks.split(",") if x.strip() != ""]
    except Exception:
        print("Erro em --ks. Use algo como: 0,1,2,3", file=sys.stderr)
        return 2

    samples = [
        (b"abracadabra", "abracadabra"),
        (b"aaaaaa", "rep"),
        (b"o rato roeu a roupa do rei de roma o rato roeu a roupa do rei de roma o rato roeu a roupa do rei de roma o rato roeu a roupa do rei de roma ", "periodic"),
    ]

    all_ok = True
    for k in ks:
        for msg, label in samples:
            res = show_case(label, k, msg, verbose=not args.no_verbose)
            all_ok = all_ok and res["ok"]

        for i in range(args.random):
            msg = os.urandom(args.rand_bytes)
            res = show_case(f"random#{i+1}", k, msg, verbose=not args.no_verbose)
            all_ok = all_ok and res["ok"]

    print("STATUS GERAL:", "OK ✅" if all_ok else "FALHOU ❌")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
