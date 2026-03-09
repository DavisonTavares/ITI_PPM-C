"""
Script de exemplo para testar rapidamente o compressor PPM-C
Execute este script para uma demonstração básica
"""

from ppm_compressor import PPMCompressor, test_compressor_with_kmax_range
import time


def demo_basic_compression():
    """Demonstração básica do compressor"""
    print("=" * 60)
    print("         DEMONSTRAÇÃO PPM-C COMPRESSOR")
    print("=" * 60)
    
    # Dados de teste variados
    test_cases = [
        {
            'name': 'Texto repetitivo',
            'data': b'hello world ' * 100,
            'description': 'Texto com muita repetição'
        },
        {
            'name': 'Sequência ABC',
            'data': b'abcabcabc' * 50,
            'description': 'Padrão simples repetido'
        },
        {
            'name': 'Dados aleatórios',
            'data': bytes(range(256)) * 2,
            'description': 'Todos os bytes possíveis'
        },
        {
            'name': 'Texto em inglês',
            'data': b'the quick brown fox jumps over the lazy dog ' * 20,
            'description': 'Frase em inglês repetida'
        }
    ]
    
    overall_results = []
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        print(f"Descrição: {test_case['description']}")
        print(f"Tamanho: {len(test_case['data'])} bytes")
        
        # Testar com diferentes k_max
        results = test_compressor_with_kmax_range(test_case['data'], max_k=5)
        
        # Encontrar melhor resultado
        best_result = min(results, key=lambda x: x['compression_ratio'])
        worst_result = max(results, key=lambda x: x['compression_ratio'])
        
        print(f"\nMelhor resultado:")
        print(f"  K_max: {best_result['k_max']}")
        print(f"  Compressão: {best_result['compression_ratio']:.4f}")
        print(f"  Economia: {(1 - best_result['compression_ratio']) * 100:.1f}%")
        print(f"  Tempo: {best_result['compression_time']:.4f}s")
        
        print(f"\nPior resultado:")
        print(f"  K_max: {worst_result['k_max']}")
        print(f"  Compressão: {worst_result['compression_ratio']:.4f}")
        
        overall_results.append({
            'name': test_case['name'],
            'best_k': best_result['k_max'],
            'best_ratio': best_result['compression_ratio'],
            'improvement': worst_result['compression_ratio'] - best_result['compression_ratio']
        })
    
    # Resumo geral
    print("\n" + "=" * 60)
    print("                RESUMO GERAL")
    print("=" * 60)
    
    print(f"{'Teste':<20} {'Melhor K':<10} {'Razão':<10} {'Melhoria':<10}")
    print("-" * 60)
    
    for result in overall_results:
        print(f"{result['name']:<20} {result['best_k']:<10} "
              f"{result['best_ratio']:<10.4f} {result['improvement']:<10.4f}")
    
    avg_improvement = sum(r['improvement'] for r in overall_results) / len(overall_results)
    print(f"\nMelhoria média ao otimizar K_max: {avg_improvement:.4f}")


def demo_compression_vs_entropy():
    """Demonstra relação entre compressão e entropia"""
    print("\n" + "=" * 60)
    print("           COMPRESSÃO vs ENTROPIA")
    print("=" * 60)
    
    # Criar dados com diferentes níveis de entropia
    entropy_tests = [
        {
            'name': 'Baixa entropia (um caractere)',
            'data': b'a' * 1000
        },
        {
            'name': 'Média entropia (dois caracteres)',
            'data': (b'ab' * 500)
        },
        {
            'name': 'Alta entropia (caracteres aleatórios)',
            'data': bytes(i % 256 for i in range(1000))
        }
    ]
    
    for test in entropy_tests:
        print(f"\n--- {test['name']} ---")
        
        compressor = PPMCompressor(k_max=3)
        compressed, stats = compressor.compress(test['data'])
        entropy = compressor.calculate_entropy(test['data'])
        
        print(f"Entropia: {entropy:.4f} bits/símbolo")
        print(f"Compressão: {stats['compression_ratio']:.4f}")
        print(f"Tamanho original: {stats['original_size']} bytes")
        print(f"Tamanho comprimido: {stats['compressed_size']} bytes")


def demo_k_max_impact():
    """Demonstra o impacto do parâmetro K_max"""
    print("\n" + "=" * 60)
    print("              IMPACTO DO K_MAX")
    print("=" * 60)
    
    # Texto com padrões de diferentes tamanhos
    test_data = b'abc' * 100 + b'defg' * 75 + b'hijkl' * 60
    
    print(f"Testando com dados de {len(test_data)} bytes")
    print("Contém padrões de tamanho 3, 4 e 5 caracteres")
    
    print(f"\n{'K_max':<6} {'Razão':<10} {'Tempo':<10} {'Economia':<10}")
    print("-" * 40)
    
    for k in range(8):
        compressor = PPMCompressor(k_max=k)
        start_time = time.time()
        compressed, stats = compressor.compress(test_data)
        
        economy = (1 - stats['compression_ratio']) * 100
        
        print(f"{k:<6} {stats['compression_ratio']:<10.4f} "
              f"{stats['compression_time']:<10.4f} {economy:<10.1f}%")


def main():
    """Função principal da demonstração"""
    print("Iniciando demonstração do PPM-C Compressor...")
    
    try:
        # Executar demonstrações
        demo_basic_compression()
        demo_compression_vs_entropy()
        demo_k_max_impact()
        
        print("\n" + "=" * 60)
        print("           DEMONSTRAÇÃO CONCLUÍDA")
        print("=" * 60)
        print("\nPara usar o sistema completo, execute: python main.py")
        
    except KeyboardInterrupt:
        print("\n\nDemonstração interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante demonstração: {e}")


if __name__ == "__main__":
    main()
