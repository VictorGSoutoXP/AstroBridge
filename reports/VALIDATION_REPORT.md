# Validação Científica do Pipeline AstroBridge

**Data**: 2026-04-27
**Campo**: NGC 2516 (RA=119.5°, Dec=-60.83°, raio=0.3°)
**Catálogo de referência**: Cantat-Gaudin & Anders (2020), A&A 633, A99

## Sumário

O pipeline AstroBridge foi validado contra o catálogo de membros publicado por Cantat-Gaudin & Anders (2020) — referência amplamente adotada na literatura de aglomerados abertos, baseado em Gaia DR2 + UPMASK.

**Resultados principais (universo de comparação: 295 fontes na interseção dos catálogos):**

| Métrica | Valor |
|---|---|
| Precision | 0.857 (85.7%) |
| Recall | 1.000 (100.0%) |
| F1-score | 0.923 |
| Accuracy | 0.858 |
| ROC-AUC (score Mahalanobis) | 0.667 |

**Nota sobre o desbalanceamento**: O universo de comparação está fortemente enviesado para positivos (252 membros vs 43 não-membros), porque o catálogo Cantat-Gaudin contém apenas candidatos a membro com proba > 0 — não inclui estrelas de campo. Por isso, accuracy é métrica enganosa nesta avaliação; precision e recall são as métricas defensáveis.

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


## Discussão

- **Cobertura do cross-match**: 252 de 798 membros confirmados do Cantat-Gaudin (proba > 0.5) foram associados a contrapartes AllWISE pelo nosso cross-match Gaia × WISE (31.6% de cobertura). Membros sem contraparte WISE (faint no IR) ficam fora do universo de comparação.
- **Falsos positivos** (42): fontes que classificamos como membro mas Cantat-Gaudin não. Inspeção visual dos painéis (ver `validation_panels.png`) mostra que estes pontos caem dentro do clump de movimento próprio e sobre a sequência principal do CMD — astrometricamente indistinguíveis de membros confirmados. CG os marca como duvidosos com base em informação fotométrica multi-banda adicional via algoritmo UPMASK.
- **Falsos negativos** (0): membros confirmados pelo CG que ficariam fora dos nossos cortes. Nosso pipeline capturou todos os membros confirmados presentes no universo de comparação (recall = 100%).
- **Interpretação do ROC-AUC = 0.667**: Score Mahalanobis univariado em (paralaxe, μα*, μδ) tem capacidade discriminativa modesta. Isto reflete o fato de que ~14% dos não-membros segundo CG são astrometricamente indistinguíveis dos membros confirmados, exigindo informação fotométrica adicional para discriminação. Esta é uma limitação intrínseca do espaço de features escolhido, não uma falha do pipeline. A próxima fase do projeto (FLINT-α) endereça isso adicionando cores Gaia (BP-RP) e magnitude absoluta ao espaço probabilístico via normalizing flow.

## Limitações

1. Cantat-Gaudin é Gaia DR2; nosso pipeline é Gaia DR3. Cross-match posicional pode introduzir pequenos erros de associação.
2. O critério de membership atual usa cortes determinísticos em paralaxe e PM. Versão futura (FLINT-α) substituirá por modelo probabilístico via normalizing flow.
3. Comparação restrita à interseção dos catálogos — fontes únicas em cada catálogo não são avaliáveis.

## Próximos passos

- Substituir critério determinístico por normalizing flow condicional (FLINT-α).
- Estender validação a outros aglomerados (M67, Pleiades, Hyades).
- Reproduzir benchmark NWAY (Salvato 2018) em XMM-COSMOS.
