"""
Script de execução completa do projeto PPM-C
Executa todos os testes e análises automaticamente
"""

import os
import time
import logging
from datetime import datetime
from ppm_compressor import test_compressor_with_kmax_range, PPMCompressor
from corpus_processor import compare_with_zip, generate_text_with_model
from analysis_utils import CompressionAnalyzer, verify_file_integrity, export_results_to_csv
import config


def setup_logging():
    """Configura logging para o projeto"""
    log_filename = f"ppm_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def create_test_files():
    """Cria arquivos de teste variados"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    
    test_files = {}
    
    # Arquivo 1: Texto repetitivo
    test_files['repetitive.txt'] = b'hello world ' * 500
    
    # Arquivo 2: Dados com padrão
    test_files['pattern.dat'] = (b'abcd' * 250)
    
    # Arquivo 3: Texto em inglês
    english_text = """
    the quick brown fox jumps over the lazy dog this is a test of the ppm compression
    algorithm which uses prediction by partial matching to compress data efficiently
    the algorithm works by building a statistical model of the data and using this
    model to predict future symbols based on the context of previous symbols the
    longer the context the better the prediction but also the more memory required
    """ * 10
    test_files['english.txt'] = english_text.encode('utf-8')
    
    # Arquivo 4: Dados binários
    test_files['binary.dat'] = bytes(range(256)) * 5
    
    # Arquivo 5: XML-like data
    xml_data = """<?xml version="1.0"?>
    <root>
        <item id="1">Test data</item>
        <item id="2">More test data</item>
        <item id="3">Even more test data</item>
    </root>""" * 20
    test_files['xml_like.xml'] = xml_data.encode('utf-8')
    
    # Salvar arquivos
    for filename, data in test_files.items():
        filepath = os.path.join(config.DATA_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(data)
    
    return test_files


def run_comprehensive_analysis(logger):
    """Executa análise compreensiva"""
    logger.info("Iniciando análise compreensiva do PPM-C")
    
    # Criar analisador
    analyzer = CompressionAnalyzer()
    
    # Criar arquivos de teste
    logger.info("Criando arquivos de teste...")
    test_files = create_test_files()
    
    all_results = []
    
    # Testar cada arquivo
    for filename, data in test_files.items():
        logger.info(f"Testando arquivo: {filename} ({len(data)} bytes)")
        
        # Limitar tamanho para velocidade
        if len(data) > config.TEST_FILE_SIZE_LIMIT:
            data = data[:config.TEST_FILE_SIZE_LIMIT]
            logger.info(f"Limitando arquivo a {len(data)} bytes")
        
        # Testar com diferentes k_max
        k_max_results = test_compressor_with_kmax_range(data, config.MAX_K)
        
        # Encontrar melhor resultado
        best_result = min(k_max_results, key=lambda x: x['compression_ratio'])
        
        # Calcular entropia
        compressor = PPMCompressor(0)
        entropy = compressor.calculate_entropy(data)
        
        # Comparar com ZIP
        filepath = os.path.join(config.DATA_DIR, filename)
        zip_comparison = compare_with_zip(filepath)
        
        # Resultado consolidado
        result = {
            'filename': filename,
            'original_size': len(data),
            'compressed_size': best_result['compressed_size'],
            'compression_ratio': best_result['compression_ratio'],
            'best_k_max': best_result['k_max'],
            'entropy': entropy,
            'compression_time': best_result['compression_time'],
            'k_max_results': k_max_results,
            'zip_ratio': zip_comparison.get('zip_ratio', 0),
            'ppm_vs_zip': best_result['compression_ratio'] / zip_comparison.get('zip_ratio', 1)
        }
        
        analyzer.add_result(result)
        all_results.append(result)
        
        logger.info(f"Melhor resultado para {filename}: k_max={best_result['k_max']}, "
                   f"ratio={best_result['compression_ratio']:.4f}")
    
    return analyzer, all_results


def generate_final_report(analyzer, all_results, logger):
    """Gera relatório final completo"""
    logger.info("Gerando relatório final...")
    
    # Criar diretório de resultados
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    
    # Relatório principal
    report_file = os.path.join(config.RESULTS_DIR, "final_report.txt")
    analyzer.generate_report(report_file)
    
    # Exportar CSV
    csv_file = os.path.join(config.RESULTS_DIR, "detailed_results.csv")
    export_results_to_csv(all_results, csv_file)
    
    # Visualizações
    try:
        viz_dir = os.path.join(config.RESULTS_DIR, config.VISUALIZATIONS_DIR)
        analyzer.create_visualizations(viz_dir)
    except Exception as e:
        logger.warning(f"Erro ao criar visualizações: {e}")
    
    # Relatório executivo
    executive_summary = os.path.join(config.RESULTS_DIR, "executive_summary.txt")
    with open(executive_summary, 'w', encoding='utf-8') as f:
        f.write("RESUMO EXECUTIVO - ANÁLISE PPM-C\n")
        f.write("=" * 50 + "\n\n")
        
        total_files = len(all_results)
        avg_compression = sum(r['compression_ratio'] for r in all_results) / total_files
        avg_time = sum(r['compression_time'] for r in all_results) / total_files
        
        best_overall = min(all_results, key=lambda x: x['compression_ratio'])
        worst_overall = max(all_results, key=lambda x: x['compression_ratio'])
        
        f.write(f"Arquivos testados: {total_files}\n")
        f.write(f"Razão média de compressão: {avg_compression:.4f}\n")
        f.write(f"Tempo médio de compressão: {avg_time:.4f}s\n\n")
        
        f.write(f"Melhor resultado: {best_overall['filename']} "
               f"(k_max={best_overall['best_k_max']}, ratio={best_overall['compression_ratio']:.4f})\n")
        f.write(f"Pior resultado: {worst_overall['filename']} "
               f"(k_max={worst_overall['best_k_max']}, ratio={worst_overall['compression_ratio']:.4f})\n\n")
        
        # Análise de k_max
        k_max_freq = {}
        for result in all_results:
            k = result['best_k_max']
            k_max_freq[k] = k_max_freq.get(k, 0) + 1
        
        f.write("Frequência de k_max ótimos:\n")
        for k in sorted(k_max_freq.keys()):
            f.write(f"  k_max {k}: {k_max_freq[k]} arquivo(s)\n")
        
        # Comparação com ZIP
        ppm_better_count = sum(1 for r in all_results if r.get('ppm_vs_zip', 1) < 1)
        f.write(f"\nPPM melhor que ZIP em {ppm_better_count}/{total_files} arquivos\n")


def test_text_generation(logger):
    """Testa geração de texto"""
    logger.info("Testando geração de texto...")
    
    try:
        # Gerar texto de exemplo
        generated_text = generate_text_with_model("dummy_model", config.DEFAULT_TEXT_LENGTH)
        
        # Salvar texto gerado
        output_file = os.path.join(config.RESULTS_DIR, "generated_text_sample.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("TEXTO GERADO PELO MODELO PPM\n")
            f.write("=" * 40 + "\n\n")
            f.write(generated_text)
        
        logger.info(f"Texto gerado salvo em: {output_file}")
        
    except Exception as e:
        logger.error(f"Erro na geração de texto: {e}")


def main():
    """Função principal de execução completa"""
    print("=" * 80)
    print("           EXECUÇÃO COMPLETA - PROJETO PPM-C")
    print("=" * 80)
    
    # Configurar logging
    logger = setup_logging()
    
    start_time = time.time()
    
    try:
        # Executar análise
        analyzer, all_results = run_comprehensive_analysis(logger)
        
        # Gerar relatórios
        generate_final_report(analyzer, all_results, logger)
        
        # Testar geração de texto
        test_text_generation(logger)
        
        total_time = time.time() - start_time
        
        logger.info(f"Análise completa concluída em {total_time:.2f} segundos")
        
        print("\n" + "=" * 80)
        print("                ANÁLISE CONCLUÍDA")
        print("=" * 80)
        print(f"Tempo total: {total_time:.2f} segundos")
        print(f"Resultados salvos em: {config.RESULTS_DIR}/")
        
        # Resumo rápido
        if all_results:
            best = min(all_results, key=lambda x: x['compression_ratio'])
            print(f"\nMelhor resultado: {best['filename']} com {best['compression_ratio']:.4f} "
                  f"(k_max={best['best_k_max']})")
            
            avg_ratio = sum(r['compression_ratio'] for r in all_results) / len(all_results)
            print(f"Razão média de compressão: {avg_ratio:.4f}")
    
    except KeyboardInterrupt:
        logger.info("Execução interrompida pelo usuário")
        print("\nExecução interrompida.")
    
    except Exception as e:
        logger.error(f"Erro durante execução: {e}")
        print(f"Erro: {e}")
    
    finally:
        print("\nPara executar análise interativa, use: python main.py")


if __name__ == "__main__":
    main()
