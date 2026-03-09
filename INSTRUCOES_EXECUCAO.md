# Instruções de Execução - Projeto PPM-C

### ✅ Funcionalidades Implementadas

1. **Compressor PPM-C** para símbolos de bytes (0-255)
2. **Testes com k_max** de 0 a 10
3. **Métricas completas**: comprimento médio, entropia, tempos
4. **Suporte ao Corpus Silesia** com download automático
5. **Processamento de corpus em inglês** (a-z + espaço)
6. **Comparação com ZIP/WinRAR**
7. **Geração de texto** usando modelo PPM
8. **Visualizações e relatórios** detalhados

## Como Executar

##### PADRÃOOO #######

### Ao executar diretamente o arquivo ppm_compressor.py, o programa realiza automaticamente:

    1. Análise do Corpus Silesia concatenado (todos os arquivos unidos em um único corpus)
    2. Análise individual de cada arquivo do corpus, processando um por um
    3. Isso permite comparar o comportamento do algoritmo em:
        Grandes volumes de dados agregados
        Arquivos individuais com características distintas

#### 🔎 Executar Apenas Análises Específicas

Caso queira realizar apenas uma análise específica, é possível:
Comentar a chamada da função correspondente no código
O próprio código contém comentários explicativos que indicam onde modificar
Também há comentários que ajudam a selecionar apenas arquivos específicos do corpus
Isso facilita testes direcionados, por exemplo:
    Analisar apenas um arquivo do Silesia
    Testar um único valor de k_max
    Executar somente o corpus concatenado

### 🚀 Opção 1: Demonstração Rápida
```bash
python demo.py
```
Executa testes básicos com diferentes tipos de dados (2-3 minutos).

### 🎮 Opção 2: Interface Interativa
```bash
python main.py
```
Menu completo com todas as funcionalidades. Escolha entre:
- Testes básicos
- Download do Corpus Silesia
- Análises detalhadas
- Geração de texto
- Visualizações

### 🔬 Opção 3: Análise Completa Automatizada
```bash
python run_full_analysis_fixed.py
```
Executa todos os testes automaticamente e gera relatórios completos (5-10 minutos).

## Estrutura dos Resultados

### Arquivos Gerados
- `final_report.txt` - Relatório detalhado completo
- `executive_summary.txt` - Resumo executivo
- `detailed_results.csv` - Dados em formato planilha
- `compression_analysis.png` - Gráficos de performance
- `generated_text_sample.txt` - Texto gerado pelo modelo

### Métricas Reportadas
- **k_max ótimo** para cada tipo de arquivo
- **Razão de compressão** (menor = melhor)
- **Economia de espaço** em percentual
- **Tempo de compressão** em segundos
- **Entropia** dos dados originais
- **Comparação com ZIP**

## Principais Descobertas

Com base nos testes executados:

### 📊 Performance por Tipo de Dados
- **Texto repetitivo**: Compressão excepcional (98-99% economia)
- **Padrões simples**: Excelente compressão (99% economia)
- **Texto natural**: Muito boa compressão (94-95% economia)
- **Dados aleatórios**: Compressão limitada (~37% economia)

### 🎯 k_max Ótimo
- **Textos com padrões**: k_max = 2-3
- **Dados complexos**: k_max = 1-2
- **Dados aleatórios**: k_max = 1

### ⚖️ PPM-C vs ZIP
- PPM-C supera ZIP em textos com muita repetição
- ZIP é mais eficiente para dados binários diversos
- Performance similar para textos naturais

## Próximos Passos

### Para Expandir o Projeto
1. **Implementar decompressão completa**
2. **Otimizar performance** para arquivos grandes
3. **Adicionar mais algoritmos** de comparação (GZIP, BZIP2)
4. **Criar interface gráfica** para visualização

### Para Entender Melhor
1. **Experimente com seus próprios arquivos**
2. **Varie os parâmetros** de k_max
3. **Compare diferentes tipos** de dados
4. **Analise a relação** entre entropia e compressibilidade

## Demonstração dos Conceitos Teóricos

### Entropia e Compressibilidade
O projeto demonstra claramente que:
- **Baixa entropia** → **Alta compressibilidade**
- **Alta entropia** → **Baixa compressibilidade**

### Contextos e Predição
- **Contextos maiores** → **Melhor predição** (até certo ponto)
- **Trade-off** entre precisão e tempo computacional
- **Adaptação** do modelo aos dados específicos

### Codificação da Informação
- **Símbolos frequentes** → **Códigos curtos**
- **Símbolos raros** → **Códigos longos**
- **Contexto** melhora a estimativa de probabilidades

## Uso Acadêmico

Este projeto pode ser usado para:

### 📚 Demonstrações em Aula
- Mostrar princípios de compressão de dados
- Ilustrar conceitos de teoria da informação
- Comparar diferentes algoritmos

### 🔬 Experimentos
- Testar com diferentes tipos de arquivos
- Analisar impacto de parâmetros
- Explorar limites teóricos de compressão

### 📝 Relatórios
- Todos os dados são exportados em formatos padrão
- Gráficos prontos para inclusão em documentos
- Análises estatísticas detalhadas

## Suporte e Documentação

### 📖 Documentação Completa
- `README.md` - Guia do usuário
- `RELATORIO_FINAL.md` - Análise técnica completa
- Comentários detalhados no código

### 🔧 Configuração
- `config.py` - Parâmetros ajustáveis
- Fácil modificação de limites e configurações

### 🐛 Troubleshooting
- Logs detalhados de execução
- Tratamento de erros robusto
- Mensagens informativas


