# Diagnóstico preliminar de membership — NGC 2516

> **Escopo corrigido (2026-08-27):** este relatório avalia um corte determinístico de
> membership dentro de uma interseção selecionada de catálogos. Ele não valida se os pares
> Gaia-AllWISE estão corretos e não constitui validação externa do motor de cross-match.

**Data**: 2026-04-27
**Campo**: NGC 2516 (RA=119.5°, Dec=-60.83°, raio=0.3°)
**Catálogo de referência**: Cantat-Gaudin & Anders (2020), A&A 633, A99

## Sumário original e reinterpretação

O diagnóstico original comparou um corte determinístico de membership com o catálogo de
membros de Cantat-Gaudin & Anders (2020), baseado em Gaia DR2 + UPMASK. Essa comparação
restrita não constitui validação do pipeline de associação AstroBridge.

**Resultados principais (universo de comparação: 295 fontes na interseção dos catálogos):**

| Métrica | Valor |
|---|---|
| Precision | 0.857 (85.7%) |
| Recall | 1.000 (100.0%) |
| F1-score | 0.923 |
| Accuracy | 0.858 |
| ROC-AUC (score Mahalanobis) | 0.667 |

**Nota sobre o desbalanceamento e a seleção:** o universo contém 252 positivos e apenas 43
negativos definidos por limiar. O classificador marcou 294 de 295 fontes como membros. Um
baseline que marca todas as fontes como membro já alcança precision = 0,854, recall = 1,000 e
F1 = 0,921, quase idêntico ao F1 = 0,923 reportado. A especificidade observada é 1/43 = 0,023
e a balanced accuracy é 0,512. Portanto, precision, recall e F1 desta amostra não demonstram
discriminação útil nem generalizam para estrelas de campo.

**Matriz de confusão:**

| | Predito não-membro | Predito membro |
|---|---|---|
| **Real não-membro** | 1 (TN) | 42 (FP) |
| **Real membro** | 0 (FN) | 252 (TP) |

## Metodologia

1. Cross-match Gaia DR3 × AllWISE realizado pelo pipeline AstroBridge V3 (notebook 01) com Bayes factor de Budavári-Szalay (2008) e resolução de unicidade via algoritmo Húngaro.
2. Membership do aglomerado definido pelo critério: paralaxe ∈ [2.0, 2.8] mas e |μα* - (-4.7)| < 2 mas/yr e |μδ - 11.2| < 2 mas/yr.
3. Catálogo Cantat-Gaudin baixado via Vizier (`J/A+A/633/A99/members`).
4. Cross-match Gaia DR3 ↔ Gaia DR2 via posição com tolerância 1″ e propagação de movimento próprio para época comum (J2016.0).
5. Ground truth: membro com PMemb (UPMASK) > 0.5.

O item 1 descreve o notebook exploratório original. O pacote `0.2.0.dev0` possui um novo motor
multi-candidato testado separadamente; este relatório não foi recalculado com esse motor.

## Estudo de Ablação

| critério                          |   precision |   recall |    F1 |   membros previstos |
|:----------------------------------|------------:|---------:|------:|--------------------:|
| só paralaxe ±0.4 mas              |       0.854 |    1     | 0.921 |                 295 |
| só paralaxe ±0.2 mas (estrito)    |       0.857 |    0.996 | 0.921 |                 293 |
| só PM ±2 mas/yr                   |       0.857 |    1     | 0.923 |                 294 |
| só PM ±1 mas/yr (estrito)         |       0.883 |    0.96  | 0.92  |                 274 |
| paralaxe ±0.4 + PM ±2 (atual)     |       0.857 |    1     | 0.923 |                 294 |
| paralaxe ±0.4 + PM ±1.5           |       0.865 |    0.988 | 0.922 |                 288 |
| paralaxe ±0.3 + PM ±1.5           |       0.865 |    0.988 | 0.922 |                 288 |
| paralaxe ±0.2 + PM ±1.0 (estrito) |       0.886 |    0.956 | 0.92  |                 272 |


## Discussão corrigida

- **Cobertura da interseção:** 252 de 798 entradas com PMemb > 0,5 aparecem na amostra
  Gaia-AllWISE usada (31,6%). Ausência pode refletir limite no infravermelho, seleção, qualidade
  ou falha de associação; este experimento não separa essas causas.
- **Falsos positivos (42):** são negativos apenas segundo o limiar PMemb > 0,5 dentro de um
  catálogo já selecionado por candidatura. Não constituem uma amostra representativa de
  estrelas de campo e não devem ser descritos como novos membros sem análise independente.
- **Falsos negativos (0):** decorrem em parte de prever praticamente todas as fontes como
  membro. Recall de 100% isoladamente não é evidência de bom desempenho.
- **ROC-AUC = 0,667:** indica discriminação modesta do score astrométrico nesta amostra. O score
  foi avaliado nos mesmos dados usados para inspecionar critérios e não possui validação
  independente.

## Limitações

1. Cantat-Gaudin é Gaia DR2; nosso pipeline é Gaia DR3. Cross-match posicional pode introduzir pequenos erros de associação.
2. O critério de membership atual usa cortes determinísticos em paralaxe e PM. Versão futura (FLINT-α) substituirá por modelo probabilístico via normalizing flow.
3. Comparação restrita à interseção dos catálogos — fontes únicas em cada catálogo não são avaliáveis.
4. O conjunto de referência não fornece uma amostra representativa de estrelas de campo.
5. A validação de membership não testa a identidade correta das contrapartes Gaia-AllWISE.
6. Não há holdout independente, intervalos de confiança ou análise de calibração.

## Próximos passos

- Validar primeiro as associações em um benchmark com verdade conhecida e em NWAY/XMM-COSMOS.
- Usar controles de campo e campos independentes para avaliação de membership.
- Reportar especificidade, balanced accuracy, curvas precision-recall e incerteza das métricas.
- Calibrar probabilidades antes de introduzir um normalizing flow condicional.
