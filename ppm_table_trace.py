# ppm_tables_side_by_side.py
# Mostra tabelas PPM-C (método C) lado a lado para K=2, K=1, K=0, K=-1 a cada iteração.

from itertools import zip_longest
import string

# Importa teu modelo (usa a estrutura que já existe no teu projeto)
from ppm_compressor import PPMModel

# ---------- helpers de formatação ----------

CTX_W = 10
SYMB_W = 5
CONT_W = 5
PROB_W = 7
GAP = "   ||   "

COL_W = CTX_W + 1 + SYMB_W + 1 + CONT_W + 1 + PROB_W  # soma de colunas + espaços

def sym_str(b: int) -> str:
    if b == 256:
        return "ρ"  # ESC
    ch = chr(b)
    printable = string.ascii_letters + string.digits + string.punctuation + " "
    return ch if ch in printable else f"\\x{b:02x}"

def ctx_str(ctx: bytes) -> str:
    printable = string.ascii_letters + string.digits + string.punctuation + " "
    s = ''.join(chr(x) if chr(x) in printable else f"\\x{x:02x}" for x in ctx)
    return s if s else "∅"

def header_lines(title: str):
    t = title.center(COL_W)
    h = (
        f"{'Contexto':<{CTX_W}} "
        f"{'Simb.':^{SYMB_W}} "
        f"{'Cont.':>{CONT_W}} "
        f"{'Prob.':>{PROB_W}}"
    )
    return [t, h]

# ---------- snapshot do modelo no método C ----------

def snapshot_ppm_c(model: PPMModel, k_max: int):
    """
    Retorna {k: {context(bytes): {'rows': [(sym,count,denom,is_esc)], 'T':T, 'r':r}}}
    onde denom = T + r (método C) e a linha de ESC é incluída como (256, r, denom, True).
    """
    out = {}
    for k in range(k_max, -1, -1):
        level = {}
        for ctx, counts in model.contexts.items():
            if len(ctx) != k or not counts:
                continue
            T = sum(counts.values())
            r = len(counts)
            denom = T + r
            rows = []
            # símbolos “reais” primeiro, ordenados
            for s in sorted(counts.keys()):
                rows.append((s, counts[s], denom, False))
            # e ESC por último
            rows.append((256, r, denom, True))
            level[ctx] = {"rows": rows, "T": T, "r": r}
        out[k] = level
    return out

def alphabet_size_from_snapshot(snapshot_level_k0: dict) -> int:
    """|A| observado a partir de K=0 (símbolos que já apareceram)."""
    seen = set()
    for ctxinfo in snapshot_level_k0.values():
        for s, c, denom, is_esc in ctxinfo["rows"]:
            if not is_esc:
                seen.add(s)
    return max(1, len(seen))

# ---------- construção das colunas (uma por K) ----------

def build_column_lines_for_k(level: dict, k_label: str):
    """
    Constrói a coluna textual para um dado nível K (dict de contextos).
    """
    lines = header_lines(f"K = {k_label}")
    if not level:
        lines.append("(vazio)".center(COL_W))
        return lines

    # Ordena contextos para estabilidade visual
    for ctx in sorted(level.keys()):
        rows = level[ctx]["rows"]
        # primeira linha com o contexto
        first = True
        for (s, c, denom, is_esc) in rows:
            prob_frac = f"{c}/{denom}"
            ctx_txt = ctx_str(ctx) if first else ""
            first = False
            line = (
                f"{ctx_txt:<{CTX_W}} "
                f"{sym_str(s):^{SYMB_W}} "
                f"{c:>{CONT_W}} "
                f"{prob_frac:>{PROB_W}}"
            )
            lines.append(line)
        # linha em branco para separar contextos (opcional)
        lines.append("".ljust(COL_W))
    return lines

def build_column_lines_for_km1(A: int):
    lines = [f"K = -1 (Equip.)".center(COL_W)]
    lines.append("".center(COL_W))
    lines.append(f"Prob. = 1/|A|".center(COL_W))
    lines.append(f"     = 1/{A}".center(COL_W))
    lines.append("".center(COL_W))
    return lines

def print_side_by_side(snapshot, k_max: int):
    # monta colunas para K=k_max, ..., 1, 0
    columns = []
    for k in range(k_max, -1, -1):
        level = snapshot.get(k, {})
        columns.append(build_column_lines_for_k(level, str(k)))

    # alfabeto para K=-1 (observado em K=0)
    A = alphabet_size_from_snapshot(snapshot.get(0, {}))
    columns.append(build_column_lines_for_km1(A))

    # normaliza alturas e imprime lado a lado
    max_h = max(len(col) for col in columns)
    for col in columns:
        while len(col) < max_h:
            col.append("".ljust(COL_W))
    for row_parts in zip_longest(*columns, fillvalue="".ljust(COL_W)):
        print(GAP.join(row_parts))

# ---------- driver: traça por iteração ----------

def trace_ppm_tables_side_by_side(data: bytes, k_max: int, show_initial=True):
    model = PPMModel(k_max)
    context = b""

    if show_initial:
        print("\n==== Modelo inicial (vazio) ====")
        snap0 = snapshot_ppm_c(model, k_max)
        print_side_by_side(snap0, k_max)

    for i, s in enumerate(data, start=1):
        model.update(context, s)
        context = (context + bytes([s]))[-k_max:]
        print("\n" + "=" * (len(GAP) * 3 + COL_W * 4))
        print(f"Após ler {i} símbolo(s): '{sym_str(s)}'")
        snap = snapshot_ppm_c(model, k_max)
        print_side_by_side(snap, k_max)

# --------------- exemplo de uso ---------------
if __name__ == "__main__":
    msg = b"abracadabra"
    trace_ppm_tables_side_by_side(msg, k_max=3, show_initial=True)
