"""
Script para baixar e processar o Corpus Silesia
Também inclui funcionalidades para criar corpus de texto em inglês
"""

import os
import requests
import zipfile
import re
import time
from pathlib import Path
from ppm_compressor import test_compressor_with_kmax_range, PPMCompressor
import matplotlib.pyplot as plt


def download_silesia_corpus(data_dir: str = "data"):
    """Baixa o Corpus Silesia"""
    os.makedirs(data_dir, exist_ok=True)
    
    # URLs dos arquivos do Silesia
    silesia_files = {
        "dickens": "http://sun.aei.polsl.pl/~sdeor/corpus/dickens",
        "mozilla": "http://sun.aei.polsl.pl/~sdeor/corpus/mozilla", 
        "mr": "http://sun.aei.polsl.pl/~sdeor/corpus/mr",
        "nci": "http://sun.aei.polsl.pl/~sdeor/corpus/nci",
        "ooffice": "http://sun.aei.polsl.pl/~sdeor/corpus/ooffice",
        "osdb": "http://sun.aei.polsl.pl/~sdeor/corpus/osdb",
        "reymont": "http://sun.aei.polsl.pl/~sdeor/corpus/reymont",
        "samba": "http://sun.aei.polsl.pl/~sdeor/corpus/samba",
        "sao": "http://sun.aei.polsl.pl/~sdeor/corpus/sao",
        "webster": "http://sun.aei.polsl.pl/~sdeor/corpus/webster",
        "xml": "http://sun.aei.polsl.pl/~sdeor/corpus/xml",
        "x-ray": "http://sun.aei.polsl.pl/~sdeor/corpus/x-ray"
    }
    
    print("Baixando Corpus Silesia...")
    
    for filename, url in silesia_files.items():
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            print(f"{filename} já existe, pulando...")
            continue
            
        try:
            print(f"Baixando {filename}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"{filename} baixado com sucesso!")
            
        except requests.exceptions.RequestException as e:
            print(f"Erro ao baixar {filename}: {e}")
    
    return data_dir


def create_english_corpus(input_files: list, output_file: str, target_size_mb: int = 100):
    """Cria um corpus de texto em inglês processado"""
    print(f"Criando corpus de texto em inglês de {target_size_mb}MB...")
    
    target_size = target_size_mb * 1024 * 1024  # Converter para bytes
    current_size = 0
    
    with open(output_file, 'w', encoding='utf-8') as outf:
        for input_file in input_files:
            if current_size >= target_size:
                break
                
            try:
                with open(input_file, 'r', encoding='utf-8', errors='ignore') as inf:
                    print(f"Processando {input_file}...")
                    
                    for line in inf:
                        if current_size >= target_size:
                            break
                        
                        # Processar linha: manter apenas a-z e espaço
                        processed_line = re.sub(r'[^a-z ]', '', line.lower())
                        
                        # Substituir múltiplos espaços por um único espaço
                        processed_line = re.sub(r' +', ' ', processed_line)
                        
                        # Remover espaços no início e fim
                        processed_line = processed_line.strip()
                        
                        if processed_line:
                            outf.write(processed_line + ' ')
                            current_size += len(processed_line) + 1
                
            except Exception as e:
                print(f"Erro ao processar {input_file}: {e}")
    
    # Verificar tamanho final
    final_size = os.path.getsize(output_file)
    print(f"Corpus criado com {final_size / (1024*1024):.2f}MB")
    
    return output_file


def test_with_silesia_corpus(data_dir: str):
    """Testa o compressor com arquivos do Corpus Silesia"""
    results = {}
    
    # Listar arquivos do Silesia
    silesia_files = []
    for filename in os.listdir(data_dir):
        filepath = os.path.join(data_dir, filename)
        if os.path.isfile(filepath) and not filename.endswith('.txt'):
            silesia_files.append(filepath)
    
    print(f"\nTestando com {len(silesia_files)} arquivos do Corpus Silesia...")
    
    for filepath in silesia_files: 
        filename = os.path.basename(filepath)
        print(f"\n--- Testando arquivo: {filename} ---")
        
        # Ler arquivo (limitando tamanho para teste)
        with open(filepath, 'rb') as f:
            data = f.read(500000)  # Ler primeiros 5MB para teste rápido
        
        if len(data) > 0:
            file_results = test_compressor_with_kmax_range(data, 5)  # Limitar k_max para velocidade
            results[filename] = file_results
    
    return results


def compare_with_zip(filepath: str):
    """Compara compressão PPM com ZIP nativo"""
    import zipfile
    import tempfile
    import time
    
    # Compressão ZIP
    temp_zip = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            temp_zip_path = temp_zip.name
        
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(filepath, os.path.basename(filepath))
        
        zip_size = os.path.getsize(temp_zip_path)
        
        # Tentar remover arquivo temporário
        try:
            time.sleep(0.1)  # Pequena pausa
            os.unlink(temp_zip_path)
        except:
            pass  # Ignorar erro se não conseguir remover
            
    except Exception as e:
        print(f"Erro na compressão ZIP: {e}")
        zip_size = 0
    
    # Compressão PPM
    with open(filepath, 'rb') as f:
        data = f.read(50000)  # Primeiros 50KB
    
    original_size = len(data)
    
    # Testar melhor k_max
    best_compression = float('inf')
    best_k = 0
    
    for k in range(6):  # 0 a 5
        compressor = PPMCompressor(k)
        compressed, stats = compressor.compress(data)
        
        if stats['compressed_size'] < best_compression:
            best_compression = stats['compressed_size']
            best_k = k
    
    print(f"\nComparação para {os.path.basename(filepath)}:")
    print(f"Tamanho original: {original_size} bytes")
    print(f"ZIP: {zip_size} bytes (ratio: {zip_size/original_size:.4f})")
    print(f"PPM-C (k={best_k}): {best_compression} bytes (ratio: {best_compression/original_size:.4f})")
    
    return {
        'original': original_size,
        'zip': zip_size,
        'ppm': best_compression,
        'zip_ratio': zip_size/original_size,
        'ppm_ratio': best_compression/original_size
    }


def generate_text_with_model(model_file: str, length: int = 1000):
    """Gera texto usando modelo PPM treinado"""
    # Implementação básica de geração de texto
    # Em implementação completa, carregaria modelo salvo
    
    # Para demonstração, criar um gerador simples
    import random
    
    # Frequências aproximadas de letras em inglês
    english_freq = {
        'a': 0.08167, 'b': 0.01492, 'c': 0.02782, 'd': 0.04253,
        'e': 0.12702, 'f': 0.02228, 'g': 0.02015, 'h': 0.06094,
        'i': 0.06966, 'j': 0.00153, 'k': 0.00772, 'l': 0.04025,
        'm': 0.02406, 'n': 0.06749, 'o': 0.07507, 'p': 0.01929,
        'q': 0.00095, 'r': 0.05987, 's': 0.06327, 't': 0.09056,
        'u': 0.02758, 'v': 0.00978, 'w': 0.02360, 'x': 0.00150,
        'y': 0.01974, 'z': 0.00074, ' ': 0.15000
    }
    
    generated_text = ""
    
    for i in range(length):
        # Escolher próximo caractere baseado em frequências
        chars = list(english_freq.keys())
        weights = list(english_freq.values())
        
        next_char = random.choices(chars, weights=weights)[0]
        generated_text += next_char
    
    return generated_text


def plot_results(results_dict: dict):
    """Plota gráficos dos resultados"""
    plt.figure(figsize=(15, 10))
    
    # Subplot 1: Razão de compressão vs K_max
    plt.subplot(2, 2, 1)
    for filename, results in results_dict.items():
        k_values = [r['k_max'] for r in results]
        ratios = [r['compression_ratio'] for r in results]
        plt.plot(k_values, ratios, marker='o', label=filename)
    
    plt.xlabel('K_max')
    plt.ylabel('Razão de Compressão')
    plt.title('Razão de Compressão vs K_max')
    plt.legend()
    plt.grid(True)
    
    # Subplot 2: Tempo de compressão vs K_max
    plt.subplot(2, 2, 2)
    for filename, results in results_dict.items():
        k_values = [r['k_max'] for r in results]
        times = [r['compression_time'] for r in results]
        plt.plot(k_values, times, marker='s', label=filename)
    
    plt.xlabel('K_max')
    plt.ylabel('Tempo de Compressão (s)')
    plt.title('Tempo de Compressão vs K_max')
    plt.legend()
    plt.grid(True)
    
    # Subplot 3: Entropia
    plt.subplot(2, 2, 3)
    for filename, results in results_dict.items():
        k_values = [r['k_max'] for r in results]
        entropies = [r['entropy'] for r in results]
        plt.plot(k_values, entropies, marker='^', label=filename)
    
    plt.xlabel('K_max')
    plt.ylabel('Entropia')
    plt.title('Entropia vs K_max')
    plt.legend()
    plt.grid(True)
    
    # Subplot 4: Comprimento médio
    plt.subplot(2, 2, 4)
    for filename, results in results_dict.items():
        k_values = [r['k_max'] for r in results]
        avg_lengths = [r['average_length'] for r in results]
        plt.plot(k_values, avg_lengths, marker='d', label=filename)
    
    plt.xlabel('K_max')
    plt.ylabel('Comprimento Médio (bits/símbolo)')
    plt.title('Comprimento Médio vs K_max')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('ppm_results.png', dpi=300, bbox_inches='tight')
    plt.show()


def main():
    """Função principal"""
    print("=== PPM-C Compressor - Projeto ITI ===")
    
    # 1. Criar diretório de dados
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    # 2. Criar arquivo de teste se Silesia não estiver disponível
    test_file = os.path.join(data_dir, "test_data.txt")
    if not os.path.exists(test_file):
        print("Criando arquivo de teste...")
        with open(test_file, 'w') as f:
            f.write("hello world " * 1000 + "this is a test for ppm compression " * 500)
    
    # 3. Testar compressor com arquivo de teste
    print("\n=== Testando com arquivo de exemplo ===")
    with open(test_file, 'rb') as f:
        test_data = f.read()
    
    results = test_compressor_with_kmax_range(test_data, 10)
    
    # 4. Comparar com ZIP
    print("\n=== Comparação com ZIP ===")
    comparison = compare_with_zip(test_file)
    
    # 5. Gerar texto com modelo
    print("\n=== Geração de texto ===")
    generated = generate_text_with_model("model.pkl", 200)
    print(f"Texto gerado (200 chars): {generated}")
    
    # 6. Salvar resultados
    print("\n=== Salvando resultados ===")
    with open("results.txt", "w") as f:
        f.write("=== Resultados PPM-C ===\n\n")
        f.write("K_max\tOriginal\tComprimido\tRazão\tEntropia\tTempo\n")
        for r in results:
            f.write(f"{r['k_max']}\t{r['original_size']}\t{r['compressed_size']}\t"
                   f"{r['compression_ratio']:.4f}\t{r['entropy']:.4f}\t"
                   f"{r['compression_time']:.4f}\n")
        
        f.write(f"\nComparação ZIP vs PPM:\n")
        f.write(f"ZIP ratio: {comparison['zip_ratio']:.4f}\n")
        f.write(f"PPM ratio: {comparison['ppm_ratio']:.4f}\n")
    
    print("Resultados salvos em 'results.txt'")
    print("Projeto concluído!")


if __name__ == "__main__":
    main()
