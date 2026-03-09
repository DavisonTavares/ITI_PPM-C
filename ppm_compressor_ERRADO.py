"""
PPM-C (Prediction by Partial Matching - Compression) Implementation
Compressor-descompressor para símbolos de bytes (0-255)
"""

import math
import time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import pickle

ESC = 256
RESET = 257
ALPHABET_SIZE = 258

class ArithmeticCoder:
    """Range coder com 32 bits de precisão - versão corrigida"""
    
    def __init__(self):
        self.precision = 32
        self.full = (1 << self.precision) - 1
        self.half = 1 << (self.precision - 1)
        self.quarter = 1 << (self.precision - 2)
        self.three_quarters = self.half + self.quarter
        
    def _build_cumulative(self, freqs: dict[int, int], esc_count: int):
        """Constrói tabelas de frequência cumulativa"""
        # Lista de símbolos ordenada
        symbols = sorted(freqs.keys())
        
        # Calcular total
        total = sum(freqs.values())
        if esc_count > 0:
            total += esc_count
            
        # Construir listas
        items = []
        cum = [0]
        
        for s in symbols:
            items.append((s, freqs[s]))
            cum.append(cum[-1] + freqs[s])
            
        if esc_count > 0:
            items.append((ESC, esc_count))
            cum.append(cum[-1] + esc_count)
            
        return items, cum, total
    
    def encode_symbol(self, low, high, pending, out_bits, sym, freqs, esc_count):
        """Codifica um símbolo"""
        items, cum, total = self._build_cumulative(freqs, esc_count)
        
        # Encontrar índice do símbolo
        idx = -1
        for i, (s, _) in enumerate(items):
            if s == sym:
                idx = i
                break
                
        if idx == -1:
            raise ValueError(f"Símbolo {sym} não encontrado")
            
        # Calcular novo intervalo
        range_size = high - low + 1
        high = low + (range_size * cum[idx + 1] // total) - 1
        low = low + (range_size * cum[idx] // total)
        
        # Normalizar
        while True:
            if high < self.half:
                out_bits.append(0)
                out_bits.extend([1] * pending)
                pending = 0
            elif low >= self.half:
                out_bits.append(1)
                out_bits.extend([0] * pending)
                pending = 0
                low -= self.half
                high -= self.half
            elif low >= self.quarter and high < self.three_quarters:
                pending += 1
                low -= self.quarter
                high -= self.quarter
            else:
                break
                
            low = (low << 1) & self.full
            high = ((high << 1) & self.full) | 1
            
        return low, high, pending
    
    def finish(self, low, pending, out_bits):
        """Finaliza a codificação"""
        pending += 1
        if low < self.quarter:
            out_bits.append(0)
            out_bits.extend([1] * pending)
        else:
            out_bits.append(1)
            out_bits.extend([0] * pending)
    
    def decode_symbol(self, code, low, high, bits_iter, freqs, esc_count):
        """Decodifica um símbolo"""
        items, cum, total = self._build_cumulative(freqs, esc_count)
        
        if total == 0:
            raise ValueError("Distribuição vazia")
        
        # Calcular valor
        range_size = high - low + 1
        value = ((code - low + 1) * total - 1) // range_size
        
        # Buscar símbolo (busca binária para eficiência)
        left, right = 0, len(cum) - 2
        while left < right:
            mid = (left + right + 1) // 2
            if cum[mid] <= value:
                left = mid
            else:
                right = mid - 1
        
        idx = left
        sym = items[idx][0]
        
        # Atualizar intervalo
        high = low + (range_size * cum[idx + 1] // total) - 1
        low = low + (range_size * cum[idx] // total)
        
        # Normalizar
        while True:
            if high < self.half:
                # Nada a fazer
                pass
            elif low >= self.half:
                low -= self.half
                high -= self.half
                code -= self.half
            elif low >= self.quarter and high < self.three_quarters:
                low -= self.quarter
                high -= self.quarter
                code -= self.quarter
            else:
                break
            
            low = (low << 1) & self.full
            high = ((high << 1) & self.full) | 1
            
            # Ler próximo bit
            try:
                bit = next(bits_iter)
            except StopIteration:
                bit = 0
            code = ((code << 1) & self.full) | bit
        
        return sym, code, low, high
    
    @staticmethod
    def bits_to_bytes(bits):
        """Converte bits para bytes"""
        # Garantir múltiplo de 8
        while len(bits) % 8 != 0:
            bits.append(0)
            
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if bits[i + j]:
                    byte |= (1 << (7 - j))
            result.append(byte)
        return bytes(result)
    
    @staticmethod
    def bytes_to_bits(data):
        """Converte bytes para bits"""
        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)
        return bits
class PPMModel:
    """Modelo PPM para predição por correspondência parcial"""
    
    def __init__(self, k_max: int):
        self.k_max = k_max
        self.contexts = defaultdict(lambda: defaultdict(int))  # contexto -> símbolo -> contagem
        self.context_totals = defaultdict(int)  # contexto -> total de símbolos
        self.escape_counts = defaultdict(int)  # contexto -> contagem de escape
        
    def update(self, context: bytes, symbol: int):
        """Atualiza o modelo com um novo símbolo no contexto dado"""
        for k in range(min(len(context) + 1, self.k_max + 1)):
            ctx = context[-k:] if k > 0 else b''
            ctx_key = ctx
            
            if symbol not in self.contexts[ctx_key]:
                # Primeiro aparecimento deste símbolo neste contexto
                self.escape_counts[ctx_key] += 1
            
            self.contexts[ctx_key][symbol] += 1
            self.context_totals[ctx_key] += 1
    
    def get_probabilities(self, context: bytes) -> Dict[int, float]:
        """Obtém probabilidades para o próximo símbolo dado o contexto"""
        probabilities = {}
        excluded_symbols = set()
        
        # Tentar contextos de k_max até 0
        for k in range(min(len(context), self.k_max), -1, -1):
            ctx = context[-k:] if k > 0 else b''
            ctx_key = ctx
            
            if ctx_key in self.contexts:
                # Calcular probabilidades para símbolos neste contexto
                total_count = self.context_totals[ctx_key]
                escape_count = self.escape_counts[ctx_key]
                
                if total_count > 0:
                    for symbol, count in self.contexts[ctx_key].items():
                        if symbol not in excluded_symbols:
                            prob = count / total_count
                            if symbol in probabilities:
                                probabilities[symbol] += prob * (1 - sum(probabilities.values()))
                            else:
                                probabilities[symbol] = prob
                    
                    # Adicionar símbolos vistos para exclusão
                    excluded_symbols.update(self.contexts[ctx_key].keys())
                    
                    # Probabilidade de escape
                    if escape_count > 0 and sum(probabilities.values()) < 1.0:
                        escape_prob = escape_count / total_count
                        remaining_prob = (1 - sum(probabilities.values())) * escape_prob
                        # Continuar para contexto menor
                        if remaining_prob > 0:
                            continue
                    else:
                        break
        
        # Se não há probabilidades, usar distribuição uniforme
        if not probabilities:
            probabilities = {i: 1.0/256 for i in range(256)}
        
        # Normalizar probabilidades
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v/total_prob for k, v in probabilities.items()}
        
        return probabilities
    
    def get_distribution_method_c(self, context: bytes, exclude: set) -> tuple[dict[int, int], int, int]:
        """
        Retorna (freqs, T, r) para método C no contexto.
        freqs: {símbolo: contagem} dos símbolos não excluídos
        T: soma das contagens
        r: número de símbolos distintos (vira freq do ESC)
        """
        counts = self.contexts.get(context, {})
        
        if not counts:
            return {}, 0, 0
        
        # Filtrar símbolos excluídos
        freqs = {}
        for s, c in counts.items():
            if s not in exclude:
                freqs[s] = c
        
        T = sum(freqs.values())
        r = len(freqs)
        
        return freqs, T, r


class PPMCompressor:
    """Compressor PPM-C principal - VERSÃO FINAL CORRIGIDA"""
    
    def __init__(self, k_max: int):
        self.k_max = k_max
        self.model = PPMModel(k_max)
        self.coder = ArithmeticCoder()
        
    def compress(self, data: bytes):
        start = time.time()
        low, high, pending = 0, self.coder.full, 0
        out_bits = []
        context = b''
        
        for i, s in enumerate(data):
            excl = set()
            encoded = False
            
            # Tentar contextos do maior para o menor
            for k in range(min(self.k_max, len(context)), -1, -1):
                ctx = context[-k:] if k > 0 else b''
                
                # Obter distribuição para este contexto
                freqs, T, r = self.model.get_distribution_method_c(ctx, excl)
                
                if T + r == 0:  # Contexto vazio
                    continue
                
                if s in freqs:
                    # Símbolo encontrado - codificar sem ESC
                    low, high, pending = self.coder.encode_symbol(
                        low, high, pending, out_bits, s, freqs, 0
                    )
                    encoded = True
                    break
                else:
                    # Símbolo não encontrado - codificar ESC
                    low, high, pending = self.coder.encode_symbol(
                        low, high, pending, out_bits, ESC, freqs, r
                    )
                    excl.update(freqs.keys())
                    # Continuar para próximo contexto
            
            # Se não encontrou em nenhum contexto, usar ordem -1
            if not encoded:
                # Ordem -1: todos os símbolos com probabilidade uniforme
                candidates = [i for i in range(256)]
                freqs = {i: 1 for i in candidates}
                
                low, high, pending = self.coder.encode_symbol(
                    low, high, pending, out_bits, s, freqs, 0
                )
            
            # Atualizar modelo com o símbolo atual
            self.model.update(context, s)
            
            # Atualizar contexto
            context = (context + bytes([s]))[-self.k_max:]
        
        # Finalizar codificação
        self.coder.finish(low, pending, out_bits)
        
        # Converter bits para bytes
        compressed = self.coder.bits_to_bytes(out_bits)
        
        stats = {
            'original_size': len(data),
            'compressed_size': len(compressed),
            'compression_ratio': len(compressed) / len(data) if data else 0,
            'compression_time': time.time() - start,
            'k_max': self.k_max
        }
        
        return compressed, stats
    
    def decompress(self, compressed_data: bytes, original_length: int):
        # Converter bytes para bits
        bits = self.coder.bytes_to_bits(compressed_data)
        bits.extend([0] * 64)
        it = iter(bits)
        
        # Inicializar range decoder
        low, high = 0, self.coder.full
        code = 0
        for _ in range(self.coder.precision):
            try:
                code = (code << 1) | next(it)
            except StopIteration:
                code <<= 1
        
        out = bytearray()
        model = PPMModel(self.k_max)
        context = b''
        
        while len(out) < original_length:
            excl = set()
            decoded = False
            
            # Tentar contextos do maior para o menor
            for k in range(min(self.k_max, len(context)), -1, -1):
                ctx = context[-k:] if k > 0 else b''
                
                # Obter distribuição para este contexto
                freqs, T, r = model.get_distribution_method_c(ctx, excl)
                
                # IMPORTANTE: Se o contexto está vazio, pular
                if T + r == 0:
                    continue
                
                # Decodificar símbolo deste contexto
                sym, code, low, high = self.coder.decode_symbol(
                    code, low, high, it, freqs, r
                )
                
                if sym == ESC:
                    # Símbolo ESC - excluir estes símbolos e continuar
                    excl.update(freqs.keys())
                    continue  # Continuar para próximo contexto
                else:
                    # Símbolo normal encontrado
                    out.append(sym)
                    model.update(context, sym)
                    context = (context + bytes([sym]))[-self.k_max:]
                    decoded = True
                    break
            
            # Se não encontrou em nenhum contexto, usar ordem -1
            if not decoded:
                # Ordem -1: distribuição uniforme
                freqs = {i: 1 for i in range(256)}
                
                sym, code, low, high = self.coder.decode_symbol(
                    code, low, high, it, freqs, 0
                )
                
                out.append(sym)
                model.update(context, sym)
                context = (context + bytes([sym]))[-self.k_max:]
        
        return bytes(out)
def test_compressor_with_kmax_range(test_data: bytes, max_k: int = 10) -> List[Dict]:
    """Testa o compressor com diferentes valores de k_max"""
    results = []
    
    print(f"Testando compressor PPM-C com dados de {len(test_data)} bytes")
    print("K_max\tTamanho Original\tTamanho Comprimido\tRazão\tEntropia\tTempo Comp.")
    print("-" * 80)
    
    for k in range(max_k + 1):
        compressor = PPMCompressor(k)
        
        # Comprimir
        compressed, stats = compressor.compress(test_data)
        
        # DESCOMPRIMIR
        decompressed = compressor.decompress(compressed, len(test_data))
        
        # VERIFICAR SE É IGUAL
        identical = decompressed == test_data
        
        # Calcular entropia
        entropy = compressor.calculate_entropy(test_data)
        
        result = {
            'k_max': k,
            'original_size': stats['original_size'],
            'compressed_size': stats['compressed_size'],
            'compression_ratio': stats['compression_ratio'],
            'entropy': entropy,
            'compression_time': stats['compression_time'],
            'average_length': stats['compression_ratio'] * 8,  # bits por símbolo
            'identical': identical
        }
        
        results.append(result)
        
        print(f"{k}\t{result['original_size']}\t\t{result['compressed_size']}\t\t"
              f"{result['compression_ratio']:.4f}\t{result['entropy']:.4f}\t"
              f"{result['compression_time']:.4f}s"
              f"\t{'OK' if identical else 'FAIL'}")
    
    return results



class SimplePPMCompressor:
    """Versão simplificada do PPM para debug"""
    
    def __init__(self, k_max: int):
        self.k_max = k_max
        self.model = defaultdict(lambda: defaultdict(int))
        
    def compress(self, data: bytes):
        """Compressão sem aritmética, apenas para debug do modelo"""
        context = b''
        symbols = []
        
        for s in data:
            # Encontrar melhor contexto
            found = False
            for k in range(min(self.k_max, len(context)), -1, -1):
                ctx = context[-k:] if k > 0 else b''
                
                if ctx in self.model and s in self.model[ctx]:
                    symbols.append(('ctx', k, s))
                    found = True
                    break
                    
            if not found:
                symbols.append(('literal', s))
            
            # Atualizar modelo
            for k in range(min(len(context) + 1, self.k_max + 1)):
                ctx = context[-k:] if k > 0 else b''
                self.model[ctx][s] += 1
            
            context = (context + bytes([s]))[-self.k_max:]
        
        return symbols
    
    def decompress(self, symbols, original_length: int):
        """Descompressão para debug"""
        out = bytearray()
        context = b''
        self.model = defaultdict(lambda: defaultdict(int))
        
        for item in symbols:
            if item[0] == 'literal':
                s = item[1]
                out.append(s)
            else:  # 'ctx'
                k, s = item[1], item[2]
                out.append(s)
            
            # Atualizar modelo
            for k in range(min(len(context) + 1, self.k_max + 1)):
                ctx = context[-k:] if k > 0 else b''
                self.model[ctx][s] += 1
            
            context = (context + bytes([s]))[-self.k_max:]
        
        return bytes(out)


def test_simple_ppm():
    """Testa a versão simplificada do PPM"""
    print("\n" + "="*60)
    print("TESTE DO PPM SIMPLIFICADO")
    print("="*60)
    
    test_data = b"abracadabra"
    print(f"Dados: {test_data}")
    
    compressor = SimplePPMCompressor(2)
    
    # Comprimir (versão simbólica)
    symbols = compressor.compress(test_data)
    print(f"Símbolos gerados: {symbols}")
    
    # Descomprimir
    decompressed = compressor.decompress(symbols, len(test_data))
    print(f"Decompressed: {decompressed}")
    
    # Verificar
    if decompressed == test_data:
        print("✓ OK - PPM simplificado funciona")
    else:
        print("✗ FALHA - PPM simplificado falhou")
        
        # Mostrar diferenças
        for i, (a, b) in enumerate(zip(test_data, decompressed)):
            if a != b:
                print(f"  Pos {i}: original={chr(a)}, decomp={chr(b)}")
                break

def test_with_different_data():
    """Testa o compressor com diferentes tipos de dados com debug"""
    
    test_cases = [
        (b"a" * 100, "Dados repetitivos curtos"),
        (b"Hello world! " * 10, "Texto repetido curto"),
        (bytes([i % 10 for i in range(100)]), "Dados cíclicos curtos"),
    ]
    
    print("\n" + "="*60)
    print("TESTE COM DEBUG")
    print("="*60)
    
    for data, desc in test_cases:
        print(f"\n{desc}: {len(data)} bytes")
        print(f"Primeiros 20 bytes: {data[:20]}")
        
        compressor = PPMCompressor(2)  # k_max pequeno para simplificar
        
        try:
            compressed, stats = compressor.compress(data)
            print(f"Comprimido: {len(compressed)} bytes, taxa: {stats['compression_ratio']:.4f}")
            
            decompressed = compressor.decompress(compressed, len(data))
            
            # Verificar byte a byte
            if decompressed == data:
                print("✓ OK - Dados idênticos")
            else:
                print("✗ FALHA - Dados diferentes")
                
                # Encontrar primeira diferença
                min_len = min(len(decompressed), len(data))
                for i in range(min_len):
                    if decompressed[i] != data[i]:
                        print(f"  Primeira diferença na posição {i}:")
                        print(f"    Original: {data[i]} ({chr(data[i]) if 32 <= data[i] < 127 else '?'})")
                        print(f"    Decomp:   {decompressed[i]} ({chr(decompressed[i]) if 32 <= decompressed[i] < 127 else '?'})")
                        
                        # Mostrar contexto ao redor
                        start = max(0, i-5)
                        end = min(len(data), i+5)
                        print(f"  Contexto original: {data[start:end]}")
                        print(f"  Contexto decomp:   {decompressed[start:end]}")
                        break
                
                if len(decompressed) != len(data):
                    print(f"  Tamanhos diferentes: original={len(data)}, decomp={len(decompressed)}")
                    
        except Exception as e:
            print(f"Erro: {e}")
            import traceback
            traceback.print_exc()

#if __name__ == "__main__":
#    # Testes anteriores...
#    
#    print("\n" + "="*60)
#    print("INÍCIO DA DEPURAÇÃO")
#    print("="*60)
#    
#    # 1. Testar PPM simplificado
#    test_simple_ppm()
#    
#    # 2. Testar com dados pequenos e debug
#    test_with_different_data()
#    
#    # 3. Testar com o arquivo Silesia (apenas primeiros bytes)
#    try:
#        with open('silesia.tar', 'rb') as f:
#            test_data = f.read(1000)  # Apenas primeiros 1000 bytes
#            print(f"\nTestando primeiros 1000 bytes do silesia.tar")
#            
#            compressor = PPMCompressor(3)
#            compressed, stats = compressor.compress(test_data)
#            decompressed = compressor.decompress(compressed, len(test_data))
#            
#            if decompressed == test_data:
#                print("✓ OK - Primeiros 1000 bytes OK")
#            else:
#                print("✗ FALHA - Primeiros 1000 bytes falharam")
#                
#                # Encontrar diferença
#                for i in range(min(len(test_data), len(decompressed))):
#                    if test_data[i] != decompressed[i]:
#                        print(f"Primeira diferença na posição {i}")
#                        print(f"Original: {test_data[i:i+20]}")
#                        print(f"Decomp:   {decompressed[i:i+20]}")
#                        break
#                        
#    except FileNotFoundError:
#        print("Arquivo silesia.tar não encontrado")

def test_step_by_step():
    """Testa o compressor passo a passo com debug"""
    print("\n" + "="*60)
    print("TESTE PASSO A PASSO")
    print("="*60)
    
    # Dados simples para teste
    test_data = b"ab"
    print(f"Dados: {test_data}")
    
    compressor = PPMCompressor(2)
    
    # Comprimir manualmente para ver o que acontece
    low, high, pending = 0, compressor.coder.full, 0
    out_bits = []
    context = b''
    model = compressor.model
    
    print("\n--- COMPRESSÃO ---")
    
    for i, s in enumerate(test_data):
        print(f"\nPosição {i}, símbolo: {chr(s)} ({s})")
        print(f"Contexto atual: {context}")
        
        excl = set()
        encoded = False
        
        for k in range(min(compressor.k_max, len(context)), -1, -1):
            ctx = context[-k:] if k > 0 else b''
            print(f"  Tentando k={k}, ctx={ctx}")
            
            freqs, T, r = model.get_distribution_method_c(ctx, excl)
            print(f"    freqs={dict(freqs)}, T={T}, r={r}")
            
            if T + r == 0:
                print(f"    Contexto vazio, continuando...")
                continue
            
            if s in freqs:
                print(f"    Símbolo encontrado! Codificando sem ESC")
                low, high, pending = compressor.coder.encode_symbol(
                    low, high, pending, out_bits, s, freqs, 0
                )
                encoded = True
                break
            else:
                print(f"    Símbolo não encontrado, codificando ESC")
                low, high, pending = compressor.coder.encode_symbol(
                    low, high, pending, out_bits, ESC, freqs, r
                )
                excl.update(freqs.keys())
                print(f"    Excluídos agora: {excl}")
        
        if not encoded:
            print(f"  Usando ordem -1")
            candidates = [i for i in range(256) if i not in excl]
            freqs = {i: 1 for i in candidates}
            low, high, pending = compressor.coder.encode_symbol(
                low, high, pending, out_bits, s, freqs, 0
            )
        
        model.update(context, s)
        context = (context + bytes([s]))[-compressor.k_max:]
        print(f"  Modelo atualizado, novo contexto: {context}")
        print(f"  Bits gerados até agora: {len(out_bits)}")
    
    compressor.coder.finish(low, pending, out_bits)
    compressed = compressor.coder.bits_to_bytes(out_bits)
    
    print(f"\nBits finais: {out_bits}")
    print(f"Comprimido: {compressed.hex()}")
    
    # Descomprimir manualmente
    print("\n--- DESCOMPRESSÃO ---")
    
    bits = compressor.coder.bytes_to_bits(compressed)
    bits.extend([0] * 64)
    it = iter(bits)
    
    low, high = 0, compressor.coder.full
    code = 0
    for _ in range(compressor.coder.precision):
        try:
            code = (code << 1) | next(it)
        except StopIteration:
            code <<= 1
    
    out = bytearray()
    model = PPMModel(compressor.k_max)
    context = b''
    
    while len(out) < len(test_data):
        print(f"\nPosição {len(out)}")
        print(f"Contexto atual: {context}")
        
        excl = set()
        decoded = False
        
        for k in range(min(compressor.k_max, len(context)), -1, -1):
            ctx = context[-k:] if k > 0 else b''
            print(f"  Tentando k={k}, ctx={ctx}")
            
            freqs, T, r = model.get_distribution_method_c(ctx, excl)
            print(f"    freqs={dict(freqs)}, T={T}, r={r}")
            
            if T + r == 0:
                if k == 0:
                    print(f"    Última chance - ordem -1")
                    candidates = [i for i in range(256) if i not in excl]
                    freqs = {i: 1 for i in candidates}
                    sym, code, low, high = compressor.coder.decode_symbol(
                        code, low, high, it, freqs, 0
                    )
                    print(f"    Decodificado: {chr(sym)} ({sym})")
                    out.append(sym)
                    model.update(context, sym)
                    context = (context + bytes([sym]))[-compressor.k_max:]
                    decoded = True
                    break
                continue
            
            sym, code, low, high = compressor.coder.decode_symbol(
                code, low, high, it, freqs, r
            )
            print(f"    Símbolo decodificado: {sym} ({chr(sym) if 32 <= sym < 127 else '?'})")
            
            if sym == ESC:
                print(f"    ESC encontrado, excluindo {freqs.keys()}")
                excl.update(freqs.keys())
                continue
            else:
                out.append(sym)
                model.update(context, sym)
                context = (context + bytes([sym]))[-compressor.k_max:]
                decoded = True
                break
        
        if not decoded:
            raise RuntimeError("Falha na decodificação")
    
    print(f"\nDecodificado: {bytes(out)}")
    print(f"Original: {test_data}")
    print(f"Correto: {bytes(out) == test_data}")

def test_correcao():
    """Testa se a correção funcionou"""
    print("\n" + "="*60)
    print("TESTE DA CORREÇÃO")
    print("="*60)
    
    # Teste que estava falhando
    test_data = b"ab"
    print(f"Dados de teste: {test_data}")
    
    compressor = PPMCompressor(2)
    
    # Comprimir
    compressed, stats = compressor.compress(test_data)
    print(f"Comprimido: {len(compressed)} bytes")
    
    # Descomprimir
    decompressed = compressor.decompress(compressed, len(test_data))
    print(f"Descomprimido: {decompressed}")
    
    # Verificar
    if decompressed == test_data:
        print("✓ CORREÇÃO FUNCIONOU!")
    else:
        print("✗ AINDA FALHOU")
        
        # Mostrar diferenças
        for i, (a, b) in enumerate(zip(test_data, decompressed)):
            if a != b:
                print(f"  Pos {i}: original={chr(a)} ({a}), decomp={chr(b)} ({b})")
                break


def test_with_debug():
    """Teste com debug para identificar onde ocorre a falha"""
    print("\n" + "="*60)
    print("TESTE COM DEBUG DETALHADO")
    print("="*60)
    
    # Teste que falhou
    test_data = b"hello world"
    print(f"Dados: {test_data}")
    
    compressor = PPMCompressor(2)
    
    # Comprimir
    compressed, stats = compressor.compress(test_data)
    print(f"Comprimido: {len(compressed)} bytes")
    
    # Descomprimir com debug
    bits = compressor.coder.bytes_to_bits(compressed)
    bits.extend([0] * 64)
    it = iter(bits)
    
    low, high = 0, compressor.coder.full
    code = 0
    for _ in range(compressor.coder.precision):
        try:
            code = (code << 1) | next(it)
        except StopIteration:
            code <<= 1
    
    out = bytearray()
    model = PPMModel(compressor.k_max)
    context = b''
    
    print("\n--- INÍCIO DA DESCOMPRESSÃO ---")
    
    while len(out) < len(test_data):
        print(f"\nPosição {len(out)}")
        print(f"Contexto atual: '{context.decode('ascii', errors='ignore')}'")
        
        excl = set()
        decoded = False
        
        for k in range(min(compressor.k_max, len(context)), -1, -1):
            ctx = context[-k:] if k > 0 else b''
            print(f"  Tentando k={k}, ctx='{ctx.decode('ascii', errors='ignore')}'")
            
            freqs, T, r = model.get_distribution_method_c(ctx, excl)
            print(f"    freqs={dict(freqs)}, T={T}, r={r}")
            
            if T + r == 0:
                print(f"    Contexto vazio, pulando...")
                continue
            
            sym, code, low, high = compressor.coder.decode_symbol(
                code, low, high, it, freqs, r
            )
            
            if sym == ESC:
                print(f"    ESC encontrado, excluindo {list(freqs.keys())}")
                excl.update(freqs.keys())
                continue
            else:
                char = chr(sym) if 32 <= sym < 127 else '?'
                print(f"    Símbolo: '{char}' ({sym})")
                out.append(sym)
                model.update(context, sym)
                context = (context + bytes([sym]))[-compressor.k_max:]
                decoded = True
                break
        
        if not decoded:
            print(f"  Usando ordem -1")
            freqs = {i: 1 for i in range(256)}
            sym, code, low, high = compressor.coder.decode_symbol(
                code, low, high, it, freqs, 0
            )
            char = chr(sym) if 32 <= sym < 127 else '?'
            print(f"    Símbolo: '{char}' ({sym})")
            out.append(sym)
            model.update(context, sym)
            context = (context + bytes([sym]))[-compressor.k_max:]
        
        print(f"  Out atual: '{out.decode('ascii', errors='ignore')}'")
    
    print(f"\n--- RESULTADO ---")
    print(f"Esperado: '{test_data.decode('ascii')}'")
    print(f"Obtido:   '{out.decode('ascii', errors='ignore')}'")
    print(f"Correto: {bytes(out) == test_data}")

if __name__ == "__main__":
    test_with_debug()