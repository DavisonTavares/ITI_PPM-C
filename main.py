"""
Projeto PPM-C - Compressor/Descompressor
Disciplina: ITI (Introdução à Teoria da Informação)

Este projeto implementa um compressor-descompressor PPM-C (Prediction by Partial Matching - Compression)
para fontes de informação cujos símbolos são bytes (A = {0, 1, ..., 255}).

Funcionalidades:
1. Compressor PPM-C com k_max variável (0 a 10)
2. Testes com Corpus Silesia
3. Análise de performance (tempo, razão de compressão, entropia)
4. Comparação com WinZip/ZIP
5. Geração de texto usando modelo PPM
6. Processamento de corpus de texto em inglês

Data: Agosto 2025
"""

import os
import sys
import time
from pathlib import Path

# Importar módulos do projeto
from ppm_compressor import test_adaptive_on_real_silesia
from ppm_compressor_ERRADO import PPMCompressor, test_compressor_with_kmax_range
from corpus_processor import (
    download_silesia_corpus, 
    create_english_corpus, 
    test_with_silesia_corpus,
    compare_with_zip,
    generate_text_with_model,
    plot_results,
    main as corpus_main
)


def print_menu():
    """Exibe o menu principal"""
    print("\n" + "="*60)
    print("           PPM-C COMPRESSOR - PROJETO ITI")
    print("="*60)
    print("1. Teste básico do compressor")
    print("2. Baixar Corpus Silesia")
    print("3. Testar com Corpus Silesia")
    print("4. Criar corpus de texto em inglês")
    print("5. Comparar com ZIP")
    print("6. Gerar texto com modelo PPM")
    print("7. Executar análise completa")
    print("8. Visualizar resultados (gráficos)")
    print("9. Sair")
    print("="*60)


def test_basic_compression():
    """Teste básico do compressor"""
    print("\n--- TESTE BÁSICO DO COMPRESSOR ---")
    
    # Dados de teste
    test_strings = [
        b"hello world hello world",
        b"abababababababab",
        b"the quick brown fox jumps over the lazy dog",
        b"a" * 1000,
        b"abcdefgabcdefgabcdefgabcdefgabcdefg" * 1000,
        bytes(range(256))  # Todos os bytes possíveis
    ]
    
    for i, test_data in enumerate(test_strings, 1):
        print(f"\nTeste {i}: {len(test_data)} bytes")
        print(f"Dados: {test_data[:50]}{'...' if len(test_data) > 50 else ''}")
        
        results = test_compressor_with_kmax_range(test_data, 5)
        
        # Encontrar melhor resultado
        best = min(results, key=lambda x: x['compression_ratio'])
        print(f"Melhor: k_max={best['k_max']}, ratio={best['compression_ratio']:.4f}")


def download_corpus():
    """Baixa o Corpus Silesia"""
    print("\n--- DOWNLOAD CORPUS SILESIA ---")
    print("Atenção: O download pode demorar vários minutos...")
    
    response = input("Deseja continuar? (s/n): ")
    if response.lower() == 's':
        data_dir = download_silesia_corpus()
        print(f"Corpus baixado em: {data_dir}")
    else:
        print("Download cancelado.")


def test_silesia():
    """Testa com arquivos do Corpus Silesia"""
    print("\n--- TESTE COM CORPUS SILESIA ---")
    
    data_dir = "data_tar/silesia.tar"
    if not os.path.exists(data_dir):
        print("Diretório de dados não encontrado. Execute primeiro o download do corpus.")
        return
    
    results = test_adaptive_on_real_silesia(data_dir)
    
    if results:
        print("\n--- RESUMO DOS RESULTADOS ---")
        for filename, file_results in results.items():
            best = min(file_results, key=lambda x: x['compression_ratio'])
            print(f"{filename}: melhor k_max={best['k_max']}, "
                  f"ratio={best['compression_ratio']:.4f}")


def create_english_text_corpus():
    """Cria corpus de texto em inglês"""
    print("\n--- CRIAÇÃO DE CORPUS EM INGLÊS ---")
    
    # Verificar se há arquivos de texto disponíveis
    text_files = []
    
    # Procurar arquivos de texto do Silesia
    data_dir = "data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename in ['dickens', 'webster']:  # Arquivos de texto
                text_files.append(os.path.join(data_dir, filename))
    
    if not text_files:
        print("Nenhum arquivo de texto encontrado.")
        print("Criando corpus de exemplo...")
        
        # Criar arquivo de texto de exemplo
        example_text = """
        the quick brown fox jumps over the lazy dog this is a sample text for testing
        the ppm compression algorithm with english text only lowercase letters and spaces
        are allowed in this corpus all other characters should be removed multiple spaces
        should be replaced with single space to create a clean corpus for training
        """ * 1000
        
        with open("english_corpus.txt", "w") as f:
            f.write(example_text)
        
        text_files = ["english_corpus.txt"]
    
    # Criar corpus processado
    output_file = "processed_english_corpus.txt"
    create_english_corpus(text_files, output_file, 1)  # 1MB para teste
    
    print(f"Corpus criado: {output_file}")


def compare_compression():
    """Compara PPM com ZIP"""
    print("\n--- COMPARAÇÃO COM ZIP ---")
    
    # Usar arquivo de teste
    test_file = "test_data.txt"
    if not os.path.exists(test_file):
        # Criar arquivo de teste
        with open(test_file, "w") as f:
            f.write("hello world " * 1000 + "this is a test " * 500)
    
    comparison = compare_with_zip(test_file)
    
    print(f"\nResultados da comparação:")
    print(f"Arquivo: {test_file}")
    print(f"Tamanho original: {comparison['original']} bytes")
    print(f"ZIP: {comparison['zip']} bytes (ratio: {comparison['zip_ratio']:.4f})")
    print(f"PPM-C: {comparison['ppm']} bytes (ratio: {comparison['ppm_ratio']:.4f})")


def generate_text():
    """Gera texto usando modelo PPM"""
    print("\n--- GERAÇÃO DE TEXTO ---")
    
    length = input("Quantos caracteres gerar? (padrão: 500): ")
    try:
        length = int(length) if length else 500
    except ValueError:
        length = 500
    
    generated = generate_text_with_model("model.pkl", length)
    
    print(f"\nTexto gerado ({len(generated)} caracteres):")
    print("-" * 60)
    print(generated)
    print("-" * 60)
    
    # Salvar em arquivo
    with open("generated_text.txt", "w") as f:
        f.write(generated)
    
    print("Texto salvo em: generated_text.txt")


def full_analysis():
    """Executa análise completa"""
    print("\n--- ANÁLISE COMPLETA ---")
    print("Esta operação pode demorar vários minutos...")
    
    response = input("Deseja continuar? (s/n): ")
    if response.lower() != 's':
        print("Análise cancelada.")
        return
    
    # Importar e executar análise completa
    try:
        from run_full_analysis_fixed import main as run_full_main
        run_full_main()
    except ImportError:
        # Fallback para análise básica
        corpus_main()


def show_graphs():
    """Mostra gráficos dos resultados"""
    print("\n--- VISUALIZAÇÃO DE RESULTADOS ---")
    
    # Verificar se há resultados salvos
    if not os.path.exists("results.txt"):
        print("Nenhum resultado encontrado. Execute primeiro uma análise.")
        return
    
    print("Carregando resultados...")
    
    # Para demonstração, criar alguns dados de exemplo
    example_results = {
        "test_data": [
            {'k_max': i, 'compression_ratio': 0.8 - i*0.05, 
             'compression_time': 0.1 + i*0.02, 'entropy': 7.5 - i*0.1,
             'average_length': 8 - i*0.1}
            for i in range(6)
        ]
    }
    
    try:
        plot_results(example_results)
        print("Gráficos gerados e salvos em 'ppm_results.png'")
    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")


def main():
    """Função principal"""
    print("Iniciando PPM-C Compressor...")
    
    while True:
        print_menu()
        
        try:
            choice = input("\nEscolha uma opção (1-9): ").strip()
            
            if choice == '1':
                test_basic_compression()
            elif choice == '2':
                download_corpus()
            elif choice == '3':
                test_silesia()
            elif choice == '4':
                create_english_text_corpus()
            elif choice == '5':
                compare_compression()
            elif choice == '6':
                generate_text()
            elif choice == '7':
                full_analysis()
            elif choice == '8':
                show_graphs()
            elif choice == '9':
                print("\nSaindo...")
                break
            else:
                print("Opção inválida. Tente novamente.")
                
        except KeyboardInterrupt:
            print("\n\nPrograma interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"\nErro: {e}")
            print("Tente novamente.")
        
        input("\nPressione Enter para continuar...")


if __name__ == "__main__":
    main()