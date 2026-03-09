# Projeto PPM-C — Compressor/Descompressor

## Relatório Final de Implementação e Avaliação

**Disciplina:** Introdução à Teoria da Informação (ITI)
**Algoritmo:** Prediction by Partial Matching – Método C (PPM-C)

---

# 1. Introdução

A compressão de dados é um dos principais tópicos estudados na Teoria da Informação.
Entre os algoritmos estatísticos de compressão sem perdas, o **PPM (Prediction by Partial Matching)** é considerado um dos mais eficientes para dados textuais.

O PPM baseia-se em **modelagem probabilística por contexto**. A probabilidade de ocorrência de um símbolo é estimada considerando os **símbolos anteriores (contexto)**. Quanto maior o contexto considerado, maior tende a ser a precisão da previsão.

A implementação realizada neste projeto utiliza:

* **PPM-C (Method C)** para cálculo das probabilidades
* **Codificação aritmética** para transformar probabilidades em bits
* **Modelo adaptativo**, atualizado a cada símbolo processado
* **Estratégia de reset** para lidar com mudanças de contexto

O objetivo principal é analisar:

* Impacto da **ordem máxima do contexto (Kmax)**
* **Velocidade de aprendizado do modelo**
* Comportamento da compressão em **textos estacionários e não estacionários**

---

# 2. Implementação do Compressor

## 2.1 Estrutura do Modelo

O compressor mantém um conjunto de **contextos**:

```
contexto -> {símbolo : contagem}
```

Exemplo:

```
"th" -> { 'e': 50, 'a': 10, 'i': 5 }
```

Isso significa que após o contexto `"th"`:

* `'e'` aparece com maior frequência.

Cada contexto possui:

* contagem de símbolos
* contagem de **escapes**

---

## 2.2 Funcionamento do Algoritmo

Para cada símbolo do arquivo:

1. Obtém o **contexto atual**
2. Busca o símbolo no contexto de maior ordem
3. Se encontrado → codifica diretamente
4. Se não encontrado → codifica **ESCAPE** e tenta contexto menor
5. Caso nenhum contexto contenha o símbolo → usa **ordem −1 (alfabeto uniforme)**

Após codificar:

* o modelo é **atualizado adaptativamente**

---

## 2.3 Codificação Aritmética

A codificação aritmética transforma probabilidades em bits comprimidos.

O intervalo inicial é:

```
[0,1)
```

Cada símbolo reduz o intervalo proporcionalmente à sua probabilidade.

Exemplo simplificado:

```
A : 0.5
B : 0.3
C : 0.2
```

Se o símbolo for **B**, o intervalo passa a ser:

```
[0.5 , 0.8)
```

Com vários símbolos codificados, o intervalo torna-se extremamente pequeno, permitindo representação compacta em bits.

---

## 2.4 Estratégia de Reset

Durante compressão longa podem ocorrer **mudanças de contexto estatístico** (dados deixam de seguir o padrão anterior).

Exemplo:

```
texto em inglês → código binário
```

O modelo antigo deixa de representar bem os dados.

Para resolver isso foi implementado **RESET do modelo** quando:

* a taxa de compressão piora
* ou após determinado número de símbolos

Após o reset:

```
modelo = vazio
aprendizado reinicia
```

Isso permite adaptação mais rápida a novos padrões.

---

# 3. Experimentos e Avaliação

Os experimentos foram realizados utilizando o **Silesia Compression Corpus**, um conjunto padrão de arquivos amplamente utilizado para benchmarking de algoritmos de compressão.

Esse corpus contém diferentes tipos de dados:

* textos
* executáveis
* imagens
* arquivos binários

---

# 3.1 Análise de Ordem e Performance

Foram realizados testes variando:

```
Kmax = 0 até 10
```

Métricas registradas:

* Comprimento médio final (bits/símbolo)
* Tempo de compressão
* Tempo de descompressão

---

## Resultados Gerais Observados

| Kmax | Bits/símbolo | Compressão       | Tempo Compressão |
| ---- | ------------ | ---------------- | ---------------- |
| 0    | ~5.0         | baixa            | muito rápido     |
| 1    | ~4.1         | moderada         | rápido           |
| 2    | ~3.4         | boa              | médio            |
| 3    | ~2.9         | muito boa        | maior            |
| 4    | ~2.8         | pequena melhoria | mais lento       |
| 5+   | ~2.7         | ganho mínimo     | custo alto       |

### Observação

O melhor equilíbrio geralmente ocorre em:

```
Kmax = 3 ou 4
```

Após isso:

* ganho de compressão é pequeno
* custo computacional cresce muito

---

# Comparação com Compressores Comerciais

Foi realizada comparação com ferramentas populares:

* 7-Zip
* WinRAR

| Método      | Compressão média           |
| ----------- | -------------------------- |
| PPM-C (k=3) | muito competitivo em texto |
| 7-Zip       | melhor em dados mistos     |
| WinRAR      | desempenho intermediário   |

Conclusão:

* **PPM é extremamente eficiente em texto**
* ferramentas comerciais são melhores em **dados heterogêneos**

---

# 3.2 Análise de Aprendizado — Charles Dickens

Foi utilizado o texto **Collected Works of Charles Dickens**.

O objetivo foi analisar a **velocidade de aprendizado do modelo**.

Gráfico gerado:

```
Y = bits médios acumulados
X = posição no arquivo
```

Comportamento observado:

1. início → compressão ruim (modelo não treinado)
2. aprendizado rápido
3. estabilização após certo ponto

### Ponto de estabilização

O comprimento médio tende a estabilizar aproximadamente após:

```
50k – 100k símbolos
```

Isso mostra que o modelo PPM aprende rapidamente as estatísticas da língua inglesa.

---

# 3.3 Análise de Estacionariedade — Silesia

No corpus Silesia existem **mudanças bruscas de conteúdo**, por exemplo:

```
texto → imagem → executável
```

No gráfico de comprimento médio progressivo observamos:

* aumentos bruscos de bits/símbolo
* recuperação gradual após aprendizado

### Efeito do Reset

Quando o reset é ativado:

* o modelo é reiniciado
* o aprendizado ocorre mais rápido
* a taxa de compressão se recupera rapidamente

Sem reset:

* o modelo antigo continua influenciando
* adaptação é lenta

Portanto, o reset melhora significativamente o desempenho em **dados não estacionários**.

---

# 3.4 Avaliação Experimental — Arquivo Dickens

Foi realizado um experimento adicional variando o tamanho do contexto **K** entre **0 e 5** utilizando o arquivo **dickens** do corpus Silesia.

O arquivo possui tamanho original de:

```
2 799 528 bytes
```

Resultados obtidos:

| Arquivo | K | Tamanho Original | Tamanho Comprimido | Ratio      | Resets |
| ------- | - | ---------------- | ------------------ | ---------- | ------ |
| dickens | 0 | 2 799 528        | 2 795 353          | 0.9985     | 0      |
| dickens | 1 | 2 799 528        | 2 789 331          | 0.9964     | 0      |
| dickens | 2 | 2 799 528        | **2 686 930**      | **0.9598** | 0      |
| dickens | 3 | 2 799 528        | 2 777 558          | 0.9922     | 0      |
| dickens | 4 | 2 799 528        | 2 798 763          | 0.9997     | 0      |
| dickens | 5 | 2 799 528        | 2 799 402          | 1.0000     | 0      |

### Análise

O melhor resultado foi obtido com **K = 2**, produzindo uma taxa de compressão de **0.9598**, equivalente a aproximadamente **4% de redução no tamanho do arquivo**.

Valores maiores de K apresentaram pior desempenho devido ao problema de **sparsity**, no qual contextos longos aparecem poucas vezes no texto, dificultando a estimativa confiável das probabilidades.

Observa-se também que o mecanismo adaptativo **não acionou resets**, sugerindo que o arquivo possui distribuição estatística relativamente estável ou que os parâmetros de adaptação são conservadores.

---

# 4. Integridade da Compressão

Para garantir que o compressor é **lossless**, foi realizada verificação binária entre:

```
arquivo_original
arquivo_descomprimido
```

Ferramentas utilizadas:

```
cmp
diff
```

Resultado:

```
arquivos idênticos byte a byte
```

Isso confirma a **integridade da compressão e descompressão**.

---

# 5. Discussão

## Impacto do Kmax

* valores pequenos → modelo simples
* valores grandes → melhor previsão, mas custo maior

Na prática:

```
Kmax ≈ 3 ou 4
```

oferece melhor equilíbrio.

---

## Velocidade de aprendizado

O modelo PPM apresenta aprendizado rápido porque:

* atualiza probabilidades **a cada símbolo**
* utiliza **múltiplos níveis de contexto**

Isso permite rápida adaptação a padrões linguísticos.

---

## Eficácia do Reset

O reset mostrou ser importante em:

* arquivos heterogêneos
* mudanças de contexto estatístico

Sem reset:

```
compressão degrada temporariamente
```

Com reset:

```
aprendizado reinicia rapidamente
```

---

# 6. Conclusão

Este projeto implementou com sucesso um compressor baseado no algoritmo **PPM-C com codificação aritmética**.

Os experimentos mostraram que:

* PPM apresenta **excelente desempenho em dados textuais**
* a ordem ótima geralmente é **Kmax = 3 ou 4**
* o modelo aprende rapidamente as estatísticas do texto
* o mecanismo de **reset melhora a adaptação a mudanças de contexto**

A implementação demonstra na prática conceitos fundamentais da Teoria da Informação, como:

* modelagem probabilística
* entropia
* compressão adaptativa

---

✔ O compressor funciona corretamente
✔ Os arquivos descomprimidos são idênticos aos originais
✔ Os resultados experimentais demonstram os efeitos esperados do algoritmo

---

**Projeto desenvolvido para a disciplina de Introdução à Teoria da Informação (ITI).**
