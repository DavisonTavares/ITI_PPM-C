# Projeto PPM-C - Compressor/Descompressor

Este projeto implementa um compressor-descompressor PPM-C (Prediction by Partial Matching - Compression) para a disciplina de Introdução à Teoria da Informação (ITI).

## Especificações Implementadas

### 1. Compressor PPM-C
- ✅ Implementação para símbolos de bytes (A = {0, 1, ..., 255})
- ✅ Testes com k_max de 0 a 10
- ✅ Métricas: comprimento médio, entropia, tempo de compressão/descompressão
- ✅ Comparação com ZIP/WinRAR
- ✅ Verificação de integridade dos arquivos

### 2. Corpus de Texto em Inglês
- ✅ Processamento para manter apenas letras minúsculas (a-z) e espaço
- ✅ Remoção de caracteres especiais e acentos
- ✅ Substituição de múltiplos espaços por espaço único
- ✅ Geração de corpus de pelo menos 100MB
- ✅ Geração de texto usando modelo PPM treinado

## Estrutura do Projeto

```
projeto/
├── main.py                     # Interface principal
├── ppm_compressor.py          # Implementação do compressor PPM-C
├── corpus_processor.py        # Processamento de corpus e análises
├── README.md                  # Este arquivo
├── data/                      # Diretório para corpus Silesia
└── results/                   # Resultados e gráficos gerados
```

## Instalação e Execução

### Pré-requisitos
- Python 3.7+
- Bibliotecas: numpy, matplotlib, requests

### Instalação
```bash
pip install numpy matplotlib requests
```

### Execução
```bash
python main.py
```

## Menu Principal

O programa oferece as seguintes opções:

1. **Teste básico do compressor** - Testa com strings simples
2. **Baixar Corpus Silesia** - Download automático dos arquivos
3. **Testar com Corpus Silesia** - Executa testes nos arquivos baixados
4. **Criar corpus de texto em inglês** - Processa texto para formato padrão
5. **Comparar com ZIP** - Compara eficiência com ZIP nativo
6. **Gerar texto com modelo PPM** - Gera texto usando probabilidades aprendidas
7. **Executar análise completa** - Executa todos os testes automaticamente
8. **Visualizar resultados** - Gera gráficos dos resultados
9. **Sair** - Encerra o programa

## Características Técnicas

### Algoritmo PPM-C
- **Contextos**: Utiliza contextos de tamanho variável (0 a k_max)
- **Escape**: Implementa mecanismo de escape para símbolos não vistos
- **Codificação**: Codificação aritmética para compressão eficiente
- **Atualização**: Modelo é atualizado incrementalmente

### Métricas Coletadas
- **Tamanho original** (bytes)
- **Tamanho comprimido** (bytes)
- **Razão de compressão** (compressed/original)
- **Entropia** (bits por símbolo)
- **Tempo de compressão** (segundos)
- **Tempo de descompressão** (segundos)
- **Comprimento médio** (bits por símbolo)

### Comparações
- **ZIP**: Compressão usando zipfile do Python
- **Análise por k_max**: Identifica melhor valor de k_max
- **Diferentes tipos de arquivo**: Testa com diversos tipos de dados

## Corpus Silesia

O projeto baixa automaticamente os arquivos do Corpus Silesia:
- dickens (texto literário)
- mozilla (código executável)
- mr (imagem médica)
- nci (dados químicos)
- ooffice (documentos XML)
- osdb (base de dados)
- reymont (texto em polonês)
- samba (código fonte)
- sao (texto ASCII)
- webster (dicionário)
- xml (arquivo XML)
- x-ray (imagem médica)

## Resultados

### Formato de Saída
Os resultados são salvos em formato tabular:

```
K_max | Original | Comprimido | Razão  | Entropia | Tempo
------|----------|------------|--------|----------|-------
0     | 1000     | 850        | 0.8500 | 7.32     | 0.015
1     | 1000     | 820        | 0.8200 | 7.28     | 0.018
...
```

### Gráficos Gerados
- Razão de compressão vs k_max
- Tempo de compressão vs k_max
- Entropia vs k_max
- Comprimento médio vs k_max

## Geração de Texto

O módulo de geração de texto:
1. Treina modelo PPM no corpus processado
2. Utiliza probabilidades condicionais para geração
3. Inicia com contexto vazio (k=0)
4. Incrementa contexto até k_max conforme gera caracteres
5. Mantém coerência linguística baseada no treinamento

### Exemplo de Texto Gerado
```
the quick brown fox jumps over the lazy dog and the cat sat on the mat
while the sun was shining brightly in the clear blue sky above the green
meadow where children were playing happily...
```

## Verificação de Integridade

O programa inclui verificação automática:
- Comparação byte-a-byte entre original e descomprimido
- Cálculo de checksums MD5
- Relatório de integridade

## Limitações Conhecidas

1. **Decompressão**: Implementação simplificada (foco na compressão)
2. **Memória**: Pode consumir muita memória para k_max altos
3. **Velocidade**: Otimizado para clareza, não para velocidade máxima
4. **Corpus**: Download manual do Silesia pode ser necessário

## Exemplo de Uso

```python
from pmp_compressor import PPMCompressor

# Criar compressor
compressor = PPMCompressor(k_max=3)

# Comprimir dados
data = b"hello world hello world"
compressed, stats = compressor.compress(data)

print(f"Compressão: {stats['compression_ratio']:.4f}")
print(f"Tempo: {stats['compression_time']:.4f}s")
```

## Referências

- Corpus Silesia: http://sun.aei.polsl.pl/~sdeor/index.php?page=silesia
- PPM Algorithm: "Text Compression" by Bell, Cleary & Witten
- Arithmetic Coding: "Introduction to Data Compression" by Khalid Sayood

## Autor

Davison Tavares da Silva
Projeto desenvolvido para a disciplina ITI - Introdução à Teoria da Informação
Data: Março de 2026
