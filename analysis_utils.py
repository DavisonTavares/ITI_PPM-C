"""
Utilitários para análise e comparação do compressor PPM-C
Inclui funções para verificação de integridade, benchmarks e relatórios
"""

import os
import time
import hashlib
import subprocess
import pandas as pd
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns


class CompressionAnalyzer:
    """Classe para análise detalhada de compressão"""
    
    def __init__(self):
        self.results = []
        
    def add_result(self, result_dict: Dict):
        """Adiciona resultado à análise"""
        self.results.append(result_dict)
    
    def generate_report(self, output_file: str = "compression_report.txt"):
        """Gera relatório detalhado"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("           RELATÓRIO DE ANÁLISE PPM-C\n")
            f.write("=" * 80 + "\n\n")
            
            if not self.results:
                f.write("Nenhum resultado disponível.\n")
                return
            
            # Estatísticas gerais
            f.write("ESTATÍSTICAS GERAIS\n")
            f.write("-" * 40 + "\n")
            
            total_files = len(self.results)
            avg_compression = sum(r.get('compression_ratio', 0) for r in self.results) / total_files
            avg_time = sum(r.get('compression_time', 0) for r in self.results) / total_files
            
            f.write(f"Total de arquivos testados: {total_files}\n")
            f.write(f"Razão média de compressão: {avg_compression:.4f}\n")
            f.write(f"Tempo médio de compressão: {avg_time:.4f}s\n\n")
            
            # Resultados por arquivo
            f.write("RESULTADOS DETALHADOS\n")
            f.write("-" * 40 + "\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"\nArquivo {i}: {result.get('filename', 'Unknown')}\n")
                f.write(f"  Tamanho original: {result.get('original_size', 0):,} bytes\n")
                f.write(f"  Tamanho comprimido: {result.get('compressed_size', 0):,} bytes\n")
                f.write(f"  Razão de compressão: {result.get('compression_ratio', 0):.4f}\n")
                f.write(f"  Entropia: {result.get('entropy', 0):.4f} bits/símbolo\n")
                f.write(f"  Tempo de compressão: {result.get('compression_time', 0):.4f}s\n")
                f.write(f"  K_max ótimo: {result.get('best_k_max', 'N/A')}\n")
            
            # Análise por K_max
            f.write("\n\nANÁLISE POR K_MAX\n")
            f.write("-" * 40 + "\n")
            
            k_max_analysis = self._analyze_k_max()
            for k, stats in k_max_analysis.items():
                f.write(f"\nK_max = {k}:\n")
                f.write(f"  Razão média: {stats['avg_ratio']:.4f}\n")
                f.write(f"  Tempo médio: {stats['avg_time']:.4f}s\n")
                f.write(f"  Arquivos onde foi ótimo: {stats['optimal_count']}\n")
        
        print(f"Relatório salvo em: {output_file}")
    
    def _analyze_k_max(self) -> Dict:
        """Analisa performance por K_max"""
        k_max_stats = {}
        
        for result in self.results:
            k_results = result.get('k_max_results', [])
            for k_result in k_results:
                k = k_result.get('k_max', 0)
                if k not in k_max_stats:
                    k_max_stats[k] = {
                        'ratios': [],
                        'times': [],
                        'optimal_count': 0
                    }
                
                k_max_stats[k]['ratios'].append(k_result.get('compression_ratio', 0))
                k_max_stats[k]['times'].append(k_result.get('compression_time', 0))
                
                if k == result.get('best_k_max', -1):
                    k_max_stats[k]['optimal_count'] += 1
        
        # Calcular médias
        for k, stats in k_max_stats.items():
            stats['avg_ratio'] = sum(stats['ratios']) / len(stats['ratios']) if stats['ratios'] else 0
            stats['avg_time'] = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
        
        return k_max_stats
    
    def create_visualizations(self, output_dir: str = "visualizations"):
        """Cria visualizações dos resultados"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.results:
            print("Nenhum resultado para visualizar.")
            return
        
        # Configurar estilo
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Gráfico 1: Distribuição de razões de compressão
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        ratios = [r.get('compression_ratio', 0) for r in self.results]
        plt.hist(ratios, bins=20, alpha=0.7, edgecolor='black')
        plt.xlabel('Razão de Compressão')
        plt.ylabel('Frequência')
        plt.title('Distribuição das Razões de Compressão')
        plt.grid(True, alpha=0.3)
        
        # Gráfico 2: Tempo vs Tamanho original
        plt.subplot(2, 2, 2)
        sizes = [r.get('original_size', 0) for r in self.results]
        times = [r.get('compression_time', 0) for r in self.results]
        plt.scatter(sizes, times, alpha=0.6)
        plt.xlabel('Tamanho Original (bytes)')
        plt.ylabel('Tempo de Compressão (s)')
        plt.title('Tempo vs Tamanho do Arquivo')
        plt.grid(True, alpha=0.3)
        
        # Gráfico 3: Razão vs Entropia
        plt.subplot(2, 2, 3)
        entropies = [r.get('entropy', 0) for r in self.results]
        plt.scatter(entropies, ratios, alpha=0.6)
        plt.xlabel('Entropia (bits/símbolo)')
        plt.ylabel('Razão de Compressão')
        plt.title('Compressão vs Entropia')
        plt.grid(True, alpha=0.3)
        
        # Gráfico 4: K_max ótimo
        plt.subplot(2, 2, 4)
        k_maxs = [r.get('best_k_max', 0) for r in self.results if r.get('best_k_max') is not None]
        plt.hist(k_maxs, bins=range(12), alpha=0.7, edgecolor='black')
        plt.xlabel('K_max Ótimo')
        plt.ylabel('Frequência')
        plt.title('Distribuição de K_max Ótimos')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'compression_analysis.png'), dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Visualizações salvas em: {output_dir}")


def verify_file_integrity(original_file: str, decompressed_file: str) -> Dict:
    """Verifica integridade entre arquivo original e descomprimido"""
    
    def calculate_md5(filepath: str) -> str:
        """Calcula hash MD5 de um arquivo"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except FileNotFoundError:
            return ""
    
    result = {
        'files_exist': False,
        'sizes_match': False,
        'md5_match': False,
        'byte_by_byte_match': False,
        'original_md5': None,
        'decompressed_md5': None,
        'original_size': 0,
        'decompressed_size': 0
    }
    
    # Verificar se arquivos existem
    if not (os.path.exists(original_file) and os.path.exists(decompressed_file)):
        return result
    
    result['files_exist'] = True
    
    # Verificar tamanhos
    orig_size = os.path.getsize(original_file)
    decomp_size = os.path.getsize(decompressed_file)
    
    result['original_size'] = orig_size
    result['decompressed_size'] = decomp_size
    result['sizes_match'] = (orig_size == decomp_size)
    
    # Verificar MD5
    orig_md5 = calculate_md5(original_file)
    decomp_md5 = calculate_md5(decompressed_file)
    
    result['original_md5'] = orig_md5
    result['decompressed_md5'] = decomp_md5
    result['md5_match'] = (orig_md5 == decomp_md5) if orig_md5 and decomp_md5 else False
    
    # Verificação byte por byte (para arquivos pequenos)
    if orig_size < 1024 * 1024:  # Apenas para arquivos < 1MB
        try:
            with open(original_file, 'rb') as f1, open(decompressed_file, 'rb') as f2:
                result['byte_by_byte_match'] = (f1.read() == f2.read())
        except:
            result['byte_by_byte_match'] = False
    
    return result


def benchmark_against_standard_compressors(filepath: str) -> Dict:
    """Compara performance com compressores padrão"""
    
    results = {
        'original_size': os.path.getsize(filepath),
        'compressors': {}
    }
    
    # Testar ZIP
    try:
        import zipfile
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                start_time = time.time()
                zf.write(filepath, os.path.basename(filepath))
                compression_time = time.time() - start_time
            
            compressed_size = os.path.getsize(temp_zip.name)
            
            results['compressors']['ZIP'] = {
                'compressed_size': compressed_size,
                'compression_ratio': compressed_size / results['original_size'],
                'compression_time': compression_time
            }
            
            os.unlink(temp_zip.name)
    
    except Exception as e:
        results['compressors']['ZIP'] = {'error': str(e)}
    
    # Testar GZIP (se disponível)
    try:
        import gzip
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.gz', delete=False) as temp_gz:
            start_time = time.time()
            with open(filepath, 'rb') as f_in:
                with gzip.open(temp_gz.name, 'wb') as f_out:
                    f_out.write(f_in.read())
            compression_time = time.time() - start_time
            
            compressed_size = os.path.getsize(temp_gz.name)
            
            results['compressors']['GZIP'] = {
                'compressed_size': compressed_size,
                'compression_ratio': compressed_size / results['original_size'],
                'compression_time': compression_time
            }
            
            os.unlink(temp_gz.name)
    
    except Exception as e:
        results['compressors']['GZIP'] = {'error': str(e)}
    
    return results


def create_performance_dashboard(results_list: List[Dict], output_file: str = "dashboard.html"):
    """Cria dashboard interativo com resultados"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PPM-C Performance Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .header { background-color: #f5f5f5; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .metric { display: inline-block; margin: 10px; padding: 10px; background: #e9ecef; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PPM-C Compression Analysis Dashboard</h1>
            
            <div class="card header">
                <h2>Resumo Executivo</h2>
                <div class="metric">
                    <strong>Arquivos Testados:</strong> {total_files}
                </div>
                <div class="metric">
                    <strong>Razão Média:</strong> {avg_ratio:.4f}
                </div>
                <div class="metric">
                    <strong>Tempo Médio:</strong> {avg_time:.4f}s
                </div>
            </div>
            
            <div class="card">
                <h2>Resultados Detalhados</h2>
                <table>
                    <tr>
                        <th>Arquivo</th>
                        <th>Tamanho Original</th>
                        <th>Melhor Compressão</th>
                        <th>Razão</th>
                        <th>K_max Ótimo</th>
                        <th>Entropia</th>
                    </tr>
                    {table_rows}
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    if not results_list:
        table_rows = "<tr><td colspan='6'>Nenhum resultado disponível</td></tr>"
        avg_ratio = 0
        avg_time = 0
        total_files = 0
    else:
        total_files = len(results_list)
        avg_ratio = sum(r.get('compression_ratio', 0) for r in results_list) / total_files
        avg_time = sum(r.get('compression_time', 0) for r in results_list) / total_files
        
        table_rows = ""
        for result in results_list:
            table_rows += f"""
            <tr>
                <td>{result.get('filename', 'Unknown')}</td>
                <td>{result.get('original_size', 0):,}</td>
                <td>{result.get('compressed_size', 0):,}</td>
                <td>{result.get('compression_ratio', 0):.4f}</td>
                <td>{result.get('best_k_max', 'N/A')}</td>
                <td>{result.get('entropy', 0):.4f}</td>
            </tr>
            """
    
    final_html = html_content.format(
        total_files=total_files,
        avg_ratio=avg_ratio,
        avg_time=avg_time,
        table_rows=table_rows
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Dashboard criado: {output_file}")


def export_results_to_csv(results_list: List[Dict], output_file: str = "ppm_results.csv"):
    """Exporta resultados para CSV"""
    
    if not results_list:
        print("Nenhum resultado para exportar.")
        return
    
    # Preparar dados para DataFrame
    flattened_results = []
    
    for result in results_list:
        base_data = {
            'filename': result.get('filename', 'Unknown'),
            'original_size': result.get('original_size', 0),
            'best_compressed_size': result.get('compressed_size', 0),
            'best_compression_ratio': result.get('compression_ratio', 0),
            'best_k_max': result.get('best_k_max', 0),
            'entropy': result.get('entropy', 0),
            'best_compression_time': result.get('compression_time', 0)
        }
        
        # Adicionar resultados por k_max
        k_results = result.get('k_max_results', [])
        for k_result in k_results:
            row_data = base_data.copy()
            row_data.update({
                'k_max': k_result.get('k_max', 0),
                'compressed_size_k': k_result.get('compressed_size', 0),
                'compression_ratio_k': k_result.get('compression_ratio', 0),
                'compression_time_k': k_result.get('compression_time', 0),
                'average_length': k_result.get('average_length', 0)
            })
            flattened_results.append(row_data)
    
    # Criar DataFrame e salvar
    try:
        df = pd.DataFrame(flattened_results)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Resultados exportados para: {output_file}")
    except ImportError:
        # Fallback sem pandas
        with open(output_file, 'w', encoding='utf-8') as f:
            if flattened_results:
                # Escrever cabeçalho
                headers = list(flattened_results[0].keys())
                f.write(','.join(headers) + '\n')
                
                # Escrever dados
                for row in flattened_results:
                    values = [str(row.get(h, '')) for h in headers]
                    f.write(','.join(values) + '\n')
        
        print(f"Resultados exportados para: {output_file} (sem pandas)")


# Exemplo de uso
if __name__ == "__main__":
    # Criar analisador
    analyzer = CompressionAnalyzer()
    
    # Adicionar resultados de exemplo
    example_result = {
        'filename': 'test.txt',
        'original_size': 1000,
        'compressed_size': 750,
        'compression_ratio': 0.75,
        'entropy': 7.2,
        'compression_time': 0.15,
        'best_k_max': 3,
        'k_max_results': [
            {'k_max': 0, 'compressed_size': 800, 'compression_ratio': 0.80, 'compression_time': 0.10},
            {'k_max': 1, 'compressed_size': 770, 'compression_ratio': 0.77, 'compression_time': 0.12},
            {'k_max': 2, 'compressed_size': 760, 'compression_ratio': 0.76, 'compression_time': 0.14},
            {'k_max': 3, 'compressed_size': 750, 'compression_ratio': 0.75, 'compression_time': 0.15}
        ]
    }
    
    analyzer.add_result(example_result)
    
    # Gerar relatório e visualizações
    analyzer.generate_report()
    analyzer.create_visualizations()
    
    print("Análise concluída!")
