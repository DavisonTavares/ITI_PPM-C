"""
PPM-C (Prediction by Partial Matching - Compression) Implementation
Compressor-descompressor para símbolos de bytes (0-255)
"""

import math
import time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import pickle
import tarfile
import os

ESC = 256
RESET = 257
ALPHABET_SIZE = 258

class ArithmeticCoder:
    """Range coder com 32 bits de precisão, cumulativas inteiras."""
    def __init__(self):
        self.precision = 32
        self.full = (1 << self.precision) - 1
        self.half = (self.full >> 1) + 1
        self.quarter = (self.half >> 1)
        self.three_quarters = self.half + self.quarter

    @staticmethod
    def _build_cumulative(freqs: dict[int,int], esc_count: int):
        # constrói lista [(sym, freq)] ordenada + cumulativas
        symbols = sorted(freqs.keys())
        total = sum(freqs.values()) + esc_count
        cum = [0]
        items = []
        for s in symbols:
            items.append((s, freqs[s]))
            cum.append(cum[-1] + freqs[s])
        if esc_count > 0:
            items.append((256, esc_count))  # ESC = 256
            cum.append(cum[-1] + esc_count)
        return items, cum, total

    def encode_symbol(self, low, high, pending, out_bits, sym, freqs, esc_count):
        items, cum, total = self._build_cumulative(freqs, esc_count)
        lookup = {s: i for i, (s, _) in enumerate(items)}
        if sym not in lookup:
            raise ValueError("Símbolo não presente para encode")
        idx = lookup[sym]
        c_low = cum[idx]
        c_high = cum[idx + 1]

        rng = high - low + 1
        high = low + (rng * c_high // total) - 1
        low  = low + (rng * c_low  // total)

        while True:
            if high < self.half:
                out_bits.append(0)
                out_bits.extend([1]*pending)
                pending = 0
            elif low >= self.half:
                out_bits.append(1)
                out_bits.extend([0]*pending)
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
        pending += 1
        if low < self.quarter:
            out_bits.append(0)
            out_bits.extend([1]*pending)
        else:
            out_bits.append(1)
            out_bits.extend([0]*pending)

    @staticmethod
    def bits_to_bytes(bits):
        while len(bits) % 8:
            bits.append(0)
        b = bytearray()
        for i in range(0, len(bits), 8):
            v = 0
            for j in range(8):
                v |= (bits[i+j] << (7-j))
            b.append(v)
        return bytes(b)

    # -------- Decoder --------
    def decode_symbol(self, code, low, high, in_bits_iter, freqs, esc_count):
        items, cum, total = self._build_cumulative(freqs, esc_count)
        rng = high - low + 1
        value = ((code - low + 1)*total - 1)//rng

        # busca binária na cumulativa
        lo, hi = 0, len(cum)-1
        while lo+1 < hi:
            mid = (lo+hi)//2
            if cum[mid] <= value:
                lo = mid
            else:
                hi = mid
        idx = lo
        sym = items[idx][0]

        c_low = cum[idx]
        c_high = cum[idx+1]
        high = low + (rng * c_high // total) - 1
        low  = low + (rng * c_low  // total)

        def read_bit():
            try:
                return next(in_bits_iter)
            except StopIteration:
                return 0

        while True:
            if high < self.half:
                pass
            elif low >= self.half:
                low -= self.half; high -= self.half; code -= self.half
            elif low >= self.quarter and high < self.three_quarters:
                low -= self.quarter; high -= self.quarter; code -= self.quarter
            else:
                break
            low = (low<<1) & self.full
            high = ((high<<1) & self.full) | 1
            code = ((code<<1) & self.full) | read_bit()
        return sym, code, low, high



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
        freqs: {símbolo: contagem} só dos símbolos não excluídos
        T: soma das contagens
        r: número de símbolos distintos (vira freq do ESC)
        """
        counts = dict(self.contexts.get(context, {}))
        if not counts:
            return {}, 0, 0
        freqs = {s:c for s,c in counts.items() if s not in exclude}
        T = sum(freqs.values())
        r = len(freqs)
        return freqs, T, r



class PPMCompressor:
    """Compressor PPM-C principal"""
    
    def __init__(self, k_max: int):
        self.k_max = k_max
        self.model = PPMModel(k_max)
        self.coder = ArithmeticCoder()
        
    def compress(self, data: bytes):
        start = time.time()
        low, high, pending = 0, self.coder.full, 0
        out_bits = []
        context = b''
        total_bytes = len(data)
        bytes_processados = 0

        for s in data:
            excl = set()
            emitted = False
            
            # Tenta contextos da maior ordem até 0
            for ordem in range(min(self.k_max, len(context)), -1, -1):
                ctx = context[-ordem:] if ordem > 0 else b''
                freqs, T, r = self.model.get_distribution_method_c(ctx, excl)
                
                if T + r > 0:  # Contexto tem símbolos
                    if s in freqs:
                        # Símbolo encontrado - codifica e sai
                        low, high, pending = self.coder.encode_symbol(
                            low, high, pending, out_bits, s, freqs, r
                        )
                        emitted = True
                        break
                    else:
                        # Símbolo não encontrado - codifica ESC e continua
                        if r > 0:  # Só codifica ESC se há símbolos no contexto
                            low, high, pending = self.coder.encode_symbol(
                                low, high, pending, out_bits, 256, freqs, r
                            )
                            excl.update(freqs.keys())
            
            # Se não encontrou em nenhum contexto, usa ordem -1 (uniforme)
            if not emitted:
                candidates = [i for i in range(256) if i not in excl]
                if not candidates:  # Segurança: se todos excluídos, usa todos
                    candidates = list(range(256))
                freqs = {i: 1 for i in candidates}
                low, high, pending = self.coder.encode_symbol(
                    low, high, pending, out_bits, s, freqs, 0
                )
            
            # Atualiza a porcentagem a cada 1000 bytes (opcional)
            bytes_processados += 1
            if bytes_processados % 1000 == 0 or bytes_processados == total_bytes:
                porcentagem = (bytes_processados / total_bytes) * 100
                print(f'\rProgresso: {porcentagem:.2f}%', end='')

            # Atualiza modelo
            self.model.update(context, s)
            context = (context + bytes([s]))[-self.k_max:]
        
        self.coder.finish(low, pending, out_bits)
        compressed = self.coder.bits_to_bytes(out_bits)
        
        stats = {
            'original_size': len(data),
            'compressed_size': len(compressed),
            'compression_ratio': len(compressed)/len(data) if data else 0,
            'compression_time': time.time()-start,
            'k_max': self.k_max
        }
        return compressed, stats
    
    def decompress(self, compressed_data: bytes, original_length: int):
        # ... (código de conversão de bits igual)
        
        while len(out) < original_length:
            excl = set()
            symbol_decoded = False
            
            for ordem in range(min(self.k_max, len(context)), -1, -1):
                ctx = context[-ordem:] if ordem > 0 else b''
                freqs, T, r = model.get_distribution_method_c(ctx, excl)
                
                if T + r > 0:
                    sym, code, low, high = self.coder.decode_symbol(
                        code, low, high, it, freqs, r
                    )
                    
                    if sym == 256:  # ESC
                        excl.update(freqs.keys())
                        continue
                    else:
                        s = sym
                        symbol_decoded = True
                        break
            
            if not symbol_decoded:
                # Ordem -1: uniforme
                candidates = [i for i in range(256) if i not in excl]
                if not candidates:
                    candidates = list(range(256))
                freqs = {i: 1 for i in candidates}
                sym, code, low, high = self.coder.decode_symbol(
                    code, low, high, it, freqs, 0
                )
                s = sym
            
            out.append(s)
            model.update(context, s)
            context = (context + bytes([s]))[-self.k_max:]
        
        return bytes(out)


    
    def calculate_entropy(self, data: bytes) -> float:
        """Calcula a entropia dos dados"""
        if not data:
            return 0.0
        
        # Contar frequências
        frequencies = Counter(data)
        length = len(data)
        
        # Calcular entropia
        entropy = 0.0
        for count in frequencies.values():
            if count > 0:
                prob = count / length
                entropy -= prob * math.log2(prob)
        
        return entropy
    

class AdaptivePPMModel:
    """Modelo PPM com monitoramento de performance e reset adaptativo"""
    
    def __init__(self, k_max: int, window_size: int = 1000, threshold_percent: float = 20.0):
        self.k_max = k_max
        self.window_size = window_size
        self.threshold_percent = threshold_percent / 100.0  # converter para decimal
        
        # Modelo principal
        self.contexts = defaultdict(lambda: defaultdict(int))
        self.context_totals = defaultdict(int)
        self.escape_counts = defaultdict(int)
        
        # Monitoramento de performance
        self.compression_window = []  # Janela atual de comprimentos
        self.window_count = 0
        self.avg_compression_prev = None
        self.reset_count = 0
        self.last_reset_position = 0

        # Acompanhamento do compressor 
        self.total_symbols = 0     # total de símbolos no arquivo atual
        self.processed_symbols = 0 # quantos símbolos já processamos

    def get_distribution_method_c(self, context: bytes, exclude: set) -> tuple[dict, int, int]:
        counts = self.contexts.get(context, {})
        if not counts:
            # Ordem -1: distribuição uniforme sobre 256 símbolos
            freqs = {i: 1 for i in range(256) if i not in exclude}
            total = sum(freqs.values())
            esc_count = 0  # ordem -1 não precisa de escape
            return freqs, total, esc_count
        
        # Aplica exclusão
        freqs = {s: c for s, c in counts.items() if s not in exclude}
        total = sum(freqs.values())
        esc_count = len(counts) - len(freqs)  # símbolos excluídos → escapes
        return freqs, total, esc_count
        
    def update(self, context: bytes, symbol: int, bits_used: float = None):
        """Atualiza o modelo e monitora performance"""
        # Atualização normal do modelo
        for k in range(min(len(context) + 1, self.k_max + 1)):
            ctx = context[-k:] if k > 0 else b''
            
            # Conta escape apenas se o contexto já existe
            if ctx in self.contexts and symbol not in self.contexts[ctx]:
                self.escape_counts[ctx] += 1
            
            self.contexts[ctx][symbol] += 1
            self.context_totals[ctx] += 1
        
        # Monitoramento de performance (se bits_used fornecido)
        if bits_used is not None:
            self._monitor_performance(bits_used)
    
    def _monitor_performance(self, bits_used: float):
        """Monitora performance em janelas deslizantes"""
        self.compression_window.append(bits_used)
        self.window_count += 1
        
        # Quando a janela está cheia
        if len(self.compression_window) >= self.window_size:
            current_avg = sum(self.compression_window) / len(self.compression_window)
            
            # Compara com média anterior se existir
            if self.avg_compression_prev is not None:
                degradation = (current_avg - self.avg_compression_prev) / self.avg_compression_prev
                
                if degradation > self.threshold_percent:
                    print(f"Reset detectado na posição {self.window_count}: "
                          f"degradação de {degradation*100:.2f}%")
                    self.reset_model()
                    self.last_reset_position = self.window_count
                    self.avg_compression_prev = None  # Reset após reinicialização
                else:
                    self.avg_compression_prev = current_avg
            else:
                self.avg_compression_prev = current_avg
            
            # Limpa janela para próxima iteração
            self.compression_window = []
    
    def reset_model(self):
        """Reinicializa o modelo (limpa todas as tabelas)"""
        self.contexts.clear()
        self.context_totals.clear()
        self.escape_counts.clear()
        self.reset_count += 1
        print(f"Modelo reinicializado. Total resets: {self.reset_count}")
    
    def get_state_for_decoder(self):
        """Retorna estado atual para sincronização com decoder"""
        return {
            'reset_count': self.reset_count,
            'last_reset_position': self.last_reset_position
        }

class AdaptivePPMCompressor(PPMCompressor):
    """Compressor PPM com reset adaptativo para dados não-estacionários"""
    
    def __init__(self, k_max: int, window_size: int = 1000, threshold_percent: float = 20.0):
        super().__init__(k_max)
        self.window_size = window_size
        self.threshold_percent = threshold_percent
        self.adaptive_model = AdaptivePPMModel(k_max, window_size, threshold_percent)
        self.reset_markers = []  # Guarda posições onde resets ocorreram
        
    def compress(self, data: bytes):
        start = time.time()
        low, high, pending = 0, self.coder.full, 0
        out_bits = []
        context = b''
        total_bytes = len(data)
        bytes_processados = 0
        
        # Cabeçalho: tamanho original e parâmetros
        header = bytearray()
        header.extend(len(data).to_bytes(4, 'big'))
        header.extend(self.k_max.to_bytes(1, 'big'))
        header.extend(self.window_size.to_bytes(2, 'big'))
        header.extend(int(self.threshold_percent * 100).to_bytes(2, 'big'))
        
        # Converter cabeçalho para bits e adicionar ao início
        header_bits = self._bytes_to_bits(header)
        
        out_bits.extend(header_bits)
        
        bits_used_window = []
        
        for i, s in enumerate(data):
            excl = set()
            bits_before = len(out_bits)
            emitted = False
            
            # Codificação PPM normal
            for k in range(min(self.k_max, len(context)), -2, -1):
                ctx = context[-k:] if k > 0 else (b'' if k == 0 else None)
                
                if k == -1:
                    candidates = [i for i in range(ALPHABET_SIZE) if i not in excl]
                    if candidates:
                        freqs = {i: 1 for i in candidates}
                        low, high, pending = self.coder.encode_symbol(
                            low, high, pending, out_bits, s, freqs, 0
                        )
                        emitted = True
                        break
                else:
                    freqs, T, r = self.adaptive_model.get_distribution_method_c(ctx, excl)
                    if T + r == 0:
                        continue
                    
                    if s in freqs:
                        low, high, pending = self.coder.encode_symbol(
                            low, high, pending, out_bits, s, freqs, r
                        )
                        emitted = True
                        break
                    else:
                        if r > 0:
                            low, high, pending = self.coder.encode_symbol(
                                low, high, pending, out_bits, 256, freqs, r
                            )
                            excl.update(freqs.keys())
            
            if not emitted:
                raise RuntimeError(f"Não foi possível codificar símbolo {s}")

            # Atualiza a porcentagem a cada 1000 bytes (opcional)
            bytes_processados += 1
            if bytes_processados % 1000 == 0 or bytes_processados == total_bytes:
                porcentagem = (bytes_processados / total_bytes) * 100
                print(f'\rProgresso: {porcentagem:.2f}%', end='')

            # Calcular bits usados para este símbolo
            bits_used = len(out_bits) - bits_before
            bits_used_window.append(bits_used)
            
            # Atualizar modelo com monitoramento
            if len(bits_used_window) >= self.window_size:
                avg_bits = sum(bits_used_window) / len(bits_used_window)
                self.adaptive_model._monitor_performance(avg_bits)
                bits_used_window = []
            
            if s != RESET:
                self.adaptive_model.update(context, s)
            context = (context + bytes([s]))[-self.k_max:]
            
            # Verificar se houve reset
            if self.adaptive_model.reset_count > len(self.reset_markers):
                # codifica símbolo RESET
                freqs = {RESET: 1}

                low, high, pending = self.coder.encode_symbol(
                    low, high, pending, out_bits,
                    RESET,
                    freqs,
                    0
                )

                self.reset_markers.append(i)

                # reset modelo
                self.adaptive_model.reset_model()

                context = b''
                excl = set()

        
        self.coder.finish(low, pending, out_bits)
        compressed = self.coder.bits_to_bytes(out_bits)
        
        stats = {
            'original_size': len(data),
            'compressed_size': len(compressed),
            'compression_ratio': len(compressed)/len(data) if data else 0,
            'compression_time': time.time()-start,
            'k_max': self.k_max,
            'resets': self.adaptive_model.reset_count,
            'reset_positions': self.reset_markers
        }
        
        return compressed, stats
    
    def _bytes_to_bits(self, data: bytes) -> List[int]:
        """Converte bytes para lista de bits"""
        bits = []
        for b in data:
            for i in range(8):
                bits.append((b >> (7 - i)) & 1)
        return bits

class AdaptivePPMDecompressor:
    """Descompressor PPM que detecta resets para manter sincronia"""
    
    def __init__(self):
        self.coder = ArithmeticCoder()
        
    def decompress(self, compressed_data: bytes):
        # Ler cabeçalho
        if len(compressed_data) < 9:
            raise ValueError("Dados comprimidos muito curtos")
        
        original_length = int.from_bytes(compressed_data[0:4], 'big')
        k_max = compressed_data[4]
        window_size = int.from_bytes(compressed_data[5:7], 'big')
        threshold = int.from_bytes(compressed_data[7:9], 'big') / 100.0
        
        # Restante dos dados comprimidos
        compressed_body = compressed_data[9:]
        
        # Converter para bits
        bits = []
        for b in compressed_body:
            for i in range(8):
                bits.append((b >> (7 - i)) & 1)
        
        # Inicializar decodificador
        it = iter(bits)
        low, high = 0, self.coder.full
        code = 0
        for _ in range(self.coder.precision):
            try:
                code = (code << 1) | next(it)
            except StopIteration:
                code <<= 1
        
        # Modelo adaptativo (começa vazio)
        model = AdaptivePPMModel(k_max, window_size, threshold)
        context = b''
        out = bytearray()
        
        reset_detector = []
        bits_processed = 0
        symbols_since_reset = 0
        
        while len(out) < original_length:            
            # Decodificação normal
            excl = set()
            symbol_decoded = False
            
            for order in range(min(k_max, len(context)), -2, -1):
                if order == -1:
                    candidates = [i for i in range(ALPHABET_SIZE) if i not in excl]
                    if candidates:
                        freqs = {i: 1 for i in candidates}
                        sym, code, low, high = self.coder.decode_symbol(
                            code, low, high, it, freqs, 0
                        )
                        s = sym
                        symbol_decoded = True
                        break
                else:
                    ctx = context[-order:] if order > 0 else b''
                    freqs, T, r = model.get_distribution_method_c(ctx, excl)
                    
                    if T + r == 0:
                        continue
                    
                    # Tentar ler próximo bit para detectar padrão de reset
                    try:
                        sym, code, low, high = self.coder.decode_symbol(
                            code, low, high, it, freqs, r
                        )
                        if sym == RESET:
                            model.reset_model()
                            context = b''
                            symbols_since_reset = 0
                            continue
                    except StopIteration:
                        # Possível fim de arquivo ou padrão de reset
                        break
                    
                    if sym == 256:  # ESC
                        excl.update(freqs.keys())
                        continue
                    else:
                        s = sym
                        symbol_decoded = True
                        break
            
            out.append(s)
            symbols_since_reset += 1
            
            # Calcular bits usados (para monitoramento)
            bits_used = 1  # Aproximação
            model.update(context, s, bits_used)
            context = (context + bytes([s]))[-k_max:]
        
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
        
        # Calcular entropia
        entropy = compressor.calculate_entropy(test_data)
        
        result = {
            'k_max': k,
            'original_size': stats['original_size'],
            'compressed_size': stats['compressed_size'],
            'compression_ratio': stats['compression_ratio'],
            'entropy': entropy,
            'compression_time': stats['compression_time'],
            'average_length': stats['compression_ratio'] * 8  # bits por símbolo
        }
        
        results.append(result)
        
        print(f"{k}\t{result['original_size']}\t\t{result['compressed_size']}\t\t"
              f"{result['compression_ratio']:.4f}\t{result['entropy']:.4f}\t"
              f"{result['compression_time']:.4f}s")
    
    return results


def test_adaptive_on_silesia():
    """Testa o compressor adaptativo com dados do Corpus Silesia"""
    
    # Simular dados concatenados do Corpus Silesia
    silesia_samples = [
        (b"x" * 10000 + b"y" * 10000, "dados uniformes"),  # Fácil
        (b"".join(bytes([i % 256]) for i in range(50000)), "dados sequenciais"),  # Médio
        (b"abc" * 10000 + b"def" * 10000 + b"ghi" * 10000, "padrões alternados"),  # Difícil
    ]
    
    # Concatenar todos os samples
    test_data = b"".join(data for data, _ in silesia_samples)
    
    print("=" * 60)
    print("Teste com dados concatenados simulando Corpus Silesia")
    print(f"Tamanho total: {len(test_data)} bytes")
    print("=" * 60)
    
    # Testar sem adaptação
    print("\n--- SEM ADAPTAÇÃO (k_max=3) ---")
    compressor_normal = PPMCompressor(3)
    compressed_normal, stats_normal = compressor_normal.compress(test_data)
    print(f"Tamanho original: {stats_normal['original_size']}")
    print(f"Tamanho comprimido: {stats_normal['compressed_size']}")
    print(f"Taxa de compressão: {stats_normal['compression_ratio']:.4f}")
    
    # Testar com adaptação
    print("\n--- COM ADAPTAÇÃO (k_max=3, window=1000, threshold=20%) ---")
    compressor_adaptive = AdaptivePPMCompressor(3, window_size=1000, threshold_percent=20.0)
    compressed_adaptive, stats_adaptive = compressor_adaptive.compress(test_data)
    print(f"Tamanho original: {stats_adaptive['original_size']}")
    print(f"Tamanho comprimido: {stats_adaptive['compressed_size']}")
    print(f"Taxa de compressão: {stats_adaptive['compression_ratio']:.4f}")
    print(f"Número de resets: {stats_adaptive['resets']}")
    print(f"Posições dos resets: {stats_adaptive['reset_positions']}")
    
    # Comparação
    improvement = (stats_normal['compression_ratio'] - stats_adaptive['compression_ratio']) / stats_normal['compression_ratio'] * 100
    print(f"\nMelhoria relativa: {improvement:.2f}%")
    
    return stats_normal, stats_adaptive



def test_adaptive_on_real_silesia(tar_path="data_tar/silesia.tar", max_files=58):
    """Testa o compressor adaptativo com o arquivo real do Corpus Silesia"""
    
    print("=" * 70)
    print("Teste com Corpus Silesia real")
    print("=" * 70)
    
    # Extrair e concatenar arquivos do Silesia
    all_data = bytearray()
    file_stats = []
    
    with tarfile.open(tar_path, 'r') as tar:
        members = tar.getmembers()
        print(f"Arquivos encontrados no Silesia: {len(members)}")
        
        for i, member in enumerate(members):
            if i >= max_files:  # Limite de arquivos
                break
            #verifica se é menor que 1MB
            #if member.size > 1024 * 1024:
               #continue
            #PEGA SO O MOZILLA, QUE É O MENOR ARQUIVO DO SILESIA
            #if "ooffice" not in member.name and "xml" not in member.name:
                #continue
            if member.isfile():
                f = tar.extractfile(member)
                if f:
                    content = f.read()
                    file_stats.append({
                        'name': member.name,
                        'size': len(content)
                    })
                    all_data.extend(content)
                    print(f"  - {member.name}: {len(content)} bytes")
    
    test_data = bytes(all_data)
     
    print("-" * 70)
    print(f"TOTAL: {len(test_data)} bytes ({len(test_data)/1024/1024:.2f} MB)")
    print("=" * 70)
    
    # Testar diferentes configurações
        #{'name': 'SEM ADAPTAÇÃO', 'k_max': 7, 'adaptive': False},
    configs = [
        {'name': 'ADAPTATIVO (window=2000, th=10%, k_max= 6)', 'k_max': 6, 'window': 2000, 'threshold': 10},
        {'name': 'ADAPTATIVO (window=2000, th=10%, k_max= 5)', 'k_max': 5, 'window': 2000, 'threshold': 10},
        {'name': 'ADAPTATIVO (window=2000, th=20%, k_max= 4)', 'k_max': 4, 'window': 2000, 'threshold': 20},
        {'name': 'ADAPTATIVO (window=2000, th=25%, k_max= 3)', 'k_max': 3, 'window': 2000, 'threshold': 25},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n--- {config['name']} ---")
        
        if not config.get('adaptive', True):
            compressor = PPMCompressor(config['k_max'])
        else:
            compressor = AdaptivePPMCompressor(
                k_max=config['k_max'],
                window_size=config['window'],
                threshold_percent=config['threshold']
            )
        
        compressed, stats = compressor.compress(test_data)
        
        print(f"Tamanho original: {stats['original_size']} bytes")
        print(f"Tamanho comprimido: {stats['compressed_size']} bytes")
        print(f"Taxa de compressão: {stats['compression_ratio']:.4f} ({stats['compression_ratio']*100:.2f}%)")
        print(f"Tempo: {stats['compression_time']:.2f}s")
        
        if 'resets' in stats:
            print(f"Resets: {stats['resets']}")
            if stats['reset_positions']:
                print(f"Posições: {stats['reset_positions'][:5]}...")
        
        results.append({
            'config': config['name'],
            'ratio': stats['compression_ratio'],
            'size': stats['compressed_size'],
            'time': stats['compression_time'],
            'resets': stats.get('resets', 0)
        })
    
    # Comparar resultados
    print("\n" + "=" * 70)
    print("RESUMO DOS RESULTADOS")
    print("=" * 70)
    
    baseline = results[0]['ratio']
    
    for r in results:
        improvement = (baseline - r['ratio']) / baseline * 100
        reset_info = f", resets={r['resets']}" if r['resets'] > 0 else ""
        print(f"{r['config']:30} | taxa: {r['ratio']:.4f} | melhoria: {improvement:+.2f}% | tempo: {r['time']:.2f}s{reset_info}")
    
    return results

def test_with_specific_files(tar_path="data_tar/silesia.tar"):
    """Testa cada arquivo do Silesia individualmente"""
    
    print("=" * 70)
    print("Teste individual com arquivos do Corpus Silesia")
    print("=" * 70)
    
    files_data = []
    
    with tarfile.open(tar_path, 'r') as tar:
        for member in tar.getmembers():
            if member.isfile() and member.size > 0:
                f = tar.extractfile(member)
                if f:
                    content = f.read()
                    files_data.append({
                        'name': member.name,
                        'data': content,
                        'size': len(content)
                    })
    
    results = []
    
    for file_info in files_data:
        print(f"\n--- Arquivo: {file_info['name']} ({file_info['size']} bytes) ---")
        
        # Testar sem adaptação
        compressor_normal = PPMCompressor(3)
        compressed_normal, stats_normal = compressor_normal.compress(file_info['data'])
        
        # Testar com adaptação
        compressor_adaptive = AdaptivePPMCompressor(3, window_size=1000, threshold_percent=15)
        compressed_adaptive, stats_adaptive = compressor_adaptive.compress(file_info['data'])
        
        improvement = (stats_normal['compression_ratio'] - stats_adaptive['compression_ratio']) / stats_normal['compression_ratio'] * 100
        
        print(f"  Normal: {stats_normal['compressed_size']:6d} bytes (taxa: {stats_normal['compression_ratio']:.4f})")
        print(f"  Adaptativo: {stats_adaptive['compressed_size']:6d} bytes (taxa: {stats_adaptive['compression_ratio']:.4f}, resets: {stats_adaptive['resets']})")
        print(f"  Melhoria: {improvement:+.2f}%")
        
        results.append({
            'file': file_info['name'],
            'size': file_info['size'],
            'normal_ratio': stats_normal['compression_ratio'],
            'adaptive_ratio': stats_adaptive['compression_ratio'],
            'improvement': improvement,
            'resets': stats_adaptive['resets']
        })
    
    # Resumo final
    print("\n" + "=" * 70)
    print("RESUMO POR ARQUIVO")
    print("=" * 70)
    
    total_improvement = 0
    files_with_improvement = 0
    
    for r in results:
        print(f"{r['file']:20} | {r['size']:8d} | normal: {r['normal_ratio']:.4f} | adapt: {r['adaptive_ratio']:.4f} | melhoria: {r['improvement']:+.2f}% | resets: {r['resets']}")
        
        if r['improvement'] > 0:
            total_improvement += r['improvement']
            files_with_improvement += 1
    
    if files_with_improvement > 0:
        avg_improvement = total_improvement / files_with_improvement
        print(f"\nMédia de melhoria nos arquivos que beneficiaram: {avg_improvement:.2f}%")
        print(f"Arquivos que melhoraram: {files_with_improvement}/{len(results)}")
    
    return results

def analyze_silesia_characteristics(tar_path="data_tar/silesia.tar"):
    """Analisa características dos arquivos do Silesia para ajustar parâmetros"""
    
    print("=" * 70)
    print("Análise das características do Corpus Silesia")
    print("=" * 70)
    
    with tarfile.open(tar_path, 'r') as tar:
        for member in tar.getmembers():
            if member.isfile() and member.size > 0:
                f = tar.extractfile(member)
                if f:
                    sample = f.read(10000)  # Lê apenas amostra para análise
                    
                    # Calcular entropia
                    from collections import Counter
                    import math
                    
                    counter = Counter(sample)
                    entropy = 0
                    for count in counter.values():
                        p = count / len(sample)
                        entropy -= p * math.log2(p)
                    
                    # Detectar tipo de conteúdo
                    text_chars = sum(1 for b in sample if 32 <= b <= 126 or b in (9,10,13))
                    text_ratio = text_chars / len(sample)
                    
                    if text_ratio > 0.8:
                        content_type = "TEXTO"
                    elif text_ratio < 0.3:
                        content_type = "BINÁRIO"
                    else:
                        content_type = "MISTO"
                    
                    print(f"{member.name:20} | tam: {member.size:8d} | entropia: {entropy:.2f} | tipo: {content_type} | texto: {text_ratio:.2%}")

def test_with_specific_files_2(tar_path="data_tar/silesia.tar"):
    """Testa cada arquivo do Silesia usando apenas o PPM adaptativo variando K"""

    print("=" * 70)
    print("Teste adaptativo com K variando de 0 a 5")
    print("=" * 70)

    files_data = []

    with tarfile.open(tar_path, 'r') as tar:
        for member in tar.getmembers():
            if "dickens" not in member.name :
                 continue
            if member.isfile() and member.size > 0:
                f = tar.extractfile(member)
                if f:
                    content = f.read()
                    files_data.append({
                        'name': member.name,
                        'data': content,
                        'size': len(content)
                    })

    results = []

    for file_info in files_data:

        print(f"\n--- Arquivo: {file_info['name']} ({file_info['size']} bytes) ---")

        for k in range(0, 6):

            compressor = AdaptivePPMCompressor(
                k,
                window_size=1000,
                threshold_percent=15
            )

            compressed, stats = compressor.compress(file_info['data'])

            print(
                f"K={k} | "
                f"{stats['compressed_size']:8d} bytes | "
                f"taxa: {stats['compression_ratio']:.4f} | "
                f"resets: {stats['resets']}"
            )

            results.append({
                'file': file_info['name'],
                'k': k,
                'size': file_info['size'],
                'compressed_size': stats['compressed_size'],
                'ratio': stats['compression_ratio'],
                'resets': stats['resets']
            })

    # Resumo final
    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)

    for r in results:
        print(
            f"{r['file']:15} | "
            f"K={r['k']} | "
            f"{r['size']:8d} -> {r['compressed_size']:8d} | "
            f"ratio: {r['ratio']:.4f} | "
            f"resets: {r['resets']}"
        )

    return results

if __name__ == "__main__":
    # Verificar se o arquivo existe
    tar_path = "data_tar/silesia.tar"
    
    if not os.path.exists(tar_path):
        print(f"Arquivo {tar_path} não encontrado!")
        print("Por favor, verifique o caminho do arquivo Silesia.")
    else:
        # Primeiro, analisar características
        analyze_silesia_characteristics(tar_path)
        
        # Depois, testar configurações
        print("\n" + "=" * 70)
        print("INICIANDO TESTES DE COMPRESSÃO")
        print("=" * 70)
        
        # Teste com arquivo concatenado
        #esults = test_adaptive_on_real_silesia(tar_path)
        
        # Teste com arquivos individuais
        print("\n" + "=" * 70)
        print("TESTANDO ARQUIVOS INDIVIDUALMENTE")
        print("=" * 70)
        #individual_results = test_with_specific_files(tar_path)
        individual_results_2 = test_with_specific_files_2(tar_path)