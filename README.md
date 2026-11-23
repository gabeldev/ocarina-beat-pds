# Ocarina Beat — MVP de PDS

Jogo musical com tema de ocarina em que o jogador toca canções curtas numa **flauta doce real**. O microfone capta o áudio, o processamento digital de sinais (PDS) reconhece as notas e o ritmo e, quando a canção está certa, o jogo reage.

Tema: **Proposta 3 – Sistema de resposta a melodias**.

## Sumário

1. [Proposta](#1-proposta)
2. [Escopo](#2-escopo)
3. [O que vamos implementar](#3-o-que-vamos-implementar)
4. [Fundamentação teórica](#4-fundamentação-teórica)
5. [Atendimento aos requisitos do projeto](#5-atendimento-aos-requisitos-do-projeto)
6. [Validação](#6-validação)
7. [Plano de trabalho](#7-plano-de-trabalho)
8. [Distribuição de tarefas](#8-distribuição-de-tarefas)
9. [Como rodar](#9-como-rodar)

## 1. Proposta

O enunciado pede um sistema que reconheça uma sequência musical previamente definida e produza uma **reação inequívoca** quando a sequência correta for executada, envolvendo **ordem, intervalos e duração/ritmo conhecidos**.

Nossa variação: o jogador toca uma canção numa **flauta doce soprano** (instrumento físico). O personagem e o tema do jogo continuam sendo de ocarina; a flauta substitui a ocarina por custo e simplicidade, com aprovação do professor. O sistema:

1. captura o som pelo microfone;
2. estima a frequência fundamental e segmenta as notas (início, fim e duração);
3. compara as notas e o ritmo com um repertório de canções conhecidas;
4. dispara uma reação clara (visual e sonora) se a canção estiver correta; se estiver errada ou incompleta, **nada** dispara e o jogo mostra onde a execução divergiu.

Descrição curta:

> Toque uma canção na sua flauta e veja o jogo responder. O Ocarina Beat usa processamento digital de sinais para reconhecer as notas e o ritmo que você toca.

### Modos de jogo

| Modo | Função | Prioridade |
| --- | --- | --- |
| **Aprender** | Mostra a canção, toca a referência sonora (com o microfone mudo enquanto o jogo toca) e pede para o jogador repetir. Indica qual nota ou ritmo divergiu. | Núcleo |
| **Tocar livre** | Escuta continuamente, mostra as notas reconhecidas e dispara a reação quando as últimas notas formam uma canção do repertório. Melodia desconhecida não dispara nada. | Núcleo |
| **Desafio rítmico** | Pista de notas no estilo jogos de ritmo, com tempo. | Opcional |

## 2. Escopo

- Entrada por **flauta doce soprano germânica em Dó** via microfone. Extensão nominal Dó5–Ré7 (523–2.349 Hz); o repertório fica em Dó5–Lá6.
- Uma nota por vez, sem acordes.
- Repertório de **6 canções de *The Legend of Zelda: Ocarina of Time***: Title Theme, Saria's Song, Zelda's Lullaby, Epona's Song, Song of Time e Song of Storms. Cada canção é guardada completa (11 a 17 notas), mas reconhecida pelas 6 primeiras. Zelda's Lullaby e Epona's Song usam as mesmas notas em ordem diferente, o que testa a falsa aceitação.
- Modos Aprender e Tocar livre, interface 3D em Godot.
- Validação quantitativa e artigo técnico.

**Extensões opcionais (só com o núcleo validado):** assobio (comparação por intervalos relativos), desafio rítmico, controle de velocidade no modo Aprender, mais canções.

## 3. O que vamos implementar

### Cadeia de processamento

```mermaid
flowchart LR
    A[Flauta doce] --> B[Microfone e captura PCM]
    B --> C[Buffer, RMS e pré-processamento]
    C --> D[Estimação de frequência e confiança]
    C --> E[Detecção de início e fim]
    D --> F[Eventos: nota, início, duração]
    E --> F
    F --> G[Reconhecimento de canção]
    H[Repertório JSON] --> G
    G --> J[Jogo em Godot: notas, reação e sons]
    F --> J
    C --> K[Registros experimentais]
    G --> K
```

### Módulos

| Módulo | Responsabilidade |
| --- | --- |
| Captura | Dispositivo, taxa de amostragem efetiva, canais, amostras e perdas. |
| Buffer e pré-processamento | Janelamento, remoção de componente contínua, RMS, filtragem FIR/IIR justificada. |
| Estimador de frequência | f0 e indicador de confiança por janela: FFT com janela Hann (com interpolação do pico) comparada a autocorrelação/YIN. |
| Segmentador | Estados silêncio → ataque → nota ativa → liberação; separa nota sustentada de notas repetidas. |
| Reconhecedor | Compara as últimas notas com cada canção (notas + razões de duração); decide: reconhecida, nenhuma, ou onde divergiu. |
| Sessão e jogo | Modos Aprender e Tocar livre, histórico de notas, reinício após erro, reação. |
| Interface | Jogo 3D em Godot (personagem, cenário, reações), HUD com as notas e a divergência, menu; tela de diagnóstico no terminal (nível, frequência, nota). |
| Registro | Configuração, eventos e métricas por sessão, para validação. |

### Stack

Desenvolvimento em **Linux**, aplicação desktop, processamento local.

- **Python** (NumPy/SciPy, `sounddevice` via PortAudio): captura, PDS, segmentação, reconhecimento, lógica dos modos e sons do jogo. Tudo testado com `pytest`.
- **Godot 4** (Forward+): cena 3D, personagem animado, reações e interface.
- **Ponte UDP local em JSON** entre os dois: o serviço Python publica eventos (nota, nível, canção reconhecida, divergência...) e recebe comandos. Protocolo em [`jogo/PROTOCOLO.md`](jogo/PROTOCOLO.md).
- **Blender**: personagem e cenário próprios, modelados por script e exportados em glTF (os arquivos-fonte de arte ficam fora do repositório).

O som do jogo sai do serviço Python, que silencia o microfone enquanto toca (mais 0,3 s de margem), para o próprio som do jogo não virar nota.

### Formato do repertório

Cada canção é uma lista de notas MIDI com durações relativas em batidas, sem instantes absolutos (a canção pode começar em qualquer momento e em andamento razoável). Os intervalos são derivados das notas, então o mesmo arquivo serve ao modo absoluto (flauta) e ao relativo (assobio, no futuro).

```json
{
  "schema_version": 1,
  "id": "cancao_01",
  "nome": "Canção de exemplo",
  "fonte": "arquivo MIDI de origem",
  "transposicao_oitavas": 1,
  "instrumento": "flauta",
  "reference_a4_hz": 440.0,
  "reconhecer_primeiras": 6,
  "notes": [
    {"midi": 72, "beats": 1},
    {"midi": 76, "beats": 1},
    {"midi": 79, "beats": 2},
    {"midi": 76, "beats": 1}
  ]
}
```

(Valores ilustrativos.) Os arquivos são gerados por `experimentos/gerar_repertorio.py` a partir de MIDIs, só com a linha melódica, transpostos por oitavas inteiras para caber na extensão da flauta. Por direitos autorais, as melodias e os MIDIs ficam fora do repositório (`repertorio/` é local).

### Regras de decisão (proposta)

- Uma canção é reconhecida quando as notas do começo (as primeiras `reconhecer_primeiras` do arquivo da canção) estão **todas** certas, na ordem, com ritmo proporcional dentro da tolerância. A melodia completa serve ao modo Aprender.
- Nenhuma canção pode começar igual a outra: o gerador do repertório confere isso e aborta se dois começos coincidirem.
- Depois de um erro no modo Aprender, recomeça-se do início da canção.
- Uma nota sustentada só conta como duas se houver nova articulação (queda de energia ou novo ataque).
- Não informar nota quando o estimador não tem evidência suficiente; falha de captura não é erro musical.

## 4. Fundamentação teórica

Para cada tópico, onde ele entra no projeto.

### 4.1 Amostragem

O áudio é uma sequência `x[n] = x(nT)`, com `T = 1/fs`, e o tempo de cada amostra é `n/fs`. Pelo critério de Nyquist, `fs ≥ 2·fmax`; abaixo disso há aliasing, que não dá para desfazer depois.

**Onde entra:** justificar a taxa de captura (requisito 2 do enunciado). As fundamentais da flauta doce soprano ficam abaixo de 2,4 kHz (Dó5 a Ré7, 523 a 2.349 Hz; o repertório vai até Lá6, 1.760 Hz), então 44,1 ou 48 kHz sobram. Se decidirmos decimar para 16 kHz para reduzir custo, será preciso um filtro anti-aliasing antes. Também serve para gerar os sinais sintéticos de teste (senoides com `ω0 = 2πf/fs`).

### 4.2 Energia e filtros

- **RMS por janela:** `RMS = sqrt((1/N) Σ x[n]²)`.
- **Filtros FIR e IIR:** `y[n] = Σ b_k x[n−k]` (FIR); com realimentação, `Σ a_k y[n−k] = Σ b_k x[n−k]` (IIR). A filtragem é a convolução da entrada com a resposta ao impulso, e `H(ω)` diz como cada frequência é alterada.

**Onde entra:**
- O RMS, com limiar e histerese, decide se há som e marca início e fim de cada nota (silêncio, fala baixa e ruído de fundo não podem virar nota).
- Um passa-faixa de 400 Hz a 5 kHz remove ruído grave (ventilador, vibração, rede elétrica) e chiado antes do estimador, sem cortar o Dó5 (523 Hz) nem o 2º harmônico do Lá6. Implementado em duas versões (`src/ocarina_beat/filtros.py`): IIR Butterworth de ordem 8 em seções de 2ª ordem (atraso ≈ 0,3 ms) e FIR de 255 coeficientes com janela de Hamming (fase linear, atraso ≈ 2,7 ms). O jogo usa o FIR: o IIR borrou notas muito curtas (≈ 50 ms) nos testes. Comparação no experimento E10.
- Uma média móvel suaviza a curva de frequência entre janelas.
- Estabilidade: se o jogo tocar a referência por alto-falante, o som volta ao microfone e pode gerar microfonia ou notas falsas. Por isso o microfone é ignorado enquanto o jogo toca; com fones o problema some.

### 4.3 DFT e FFT

A DFT amostra N pontos do espectro: `X[k] = Σ x[n] e^{−j2πkn/N}`, com bins espaçados de `Δf = fs/N`. A FFT calcula isso em O(N log N). A janela de Hann reduz o vazamento espectral ao custo de um lóbulo principal mais largo, e zero-padding não aumenta a resolução física.

**Onde entra:** é o método de referência para estimar a frequência fundamental. Com `fs = 48 kHz` e `N = 2048`, `Δf ≈ 23,4 Hz`, pouco menos de um semitom em Dó5 (~31 Hz), então nas notas graves a resolução é o ponto crítico. Vamos testar interpolação parabólica do pico, janelas maiores (com mais atraso) e o método temporal da seção 4.5. Como a flauta doce soa quase como uma senoide, o pico da FFT tende a ser a fundamental, mas erros de oitava ainda podem acontecer e serão medidos.

### 4.4 Transformada Z

Polos, zeros e região de convergência descrevem um filtro. Um sistema causal só é estável com os polos dentro do círculo unitário; filtros FIR têm só zeros e são sempre estáveis.

**Onde entra:** verificar a estabilidade do filtro IIR do pré-processamento: os 8 polos do Butterworth passa-faixa ficam dentro do círculo unitário (o módulo do maior é ≈ 0,98, perto da borda por causa do corte em 400 Hz a 48 kHz, o que explica a escolha de seções de 2ª ordem). O FIR só tem zeros e é sempre estável.

### 4.5 Frequência, nota e cents

Posição MIDI `m = 69 + 12·log2(f/440)`; frequência da nota `f(k) = 440·2^((k−69)/12)`; desvio em cents `e = 1200·log2(f/f_ref)`.

**Onde entra:** converter a frequência estimada em nota e medir o quanto ela está desafinada. A comparação com o repertório usa a nota esperada, não só o arredondamento para a mais próxima, com tolerância de ±70 cents. Nos primeiros testes com a flauta, o Dó5 saiu cerca de 40 cents alto mesmo bem tocado (o Lá5 ficou afinado), e com ±50 cents ele seria lido como Dó♯5.

### 4.6 Autocorrelação e YIN

Na autocorrelação, o atraso `τ` com maior semelhança entre o sinal e ele mesmo dá `f0 = fs/τ`. É preciso restringir `τ` à faixa do instrumento e tratar múltiplos e submúltiplos do período. O YIN (de Cheveigné e Kawahara, 2002) usa uma função de diferença normalizada, com limiar e refinamento, e é mais robusto a erros de oitava.

**Onde entra:** é o segundo estimador, comparado à FFT nos mesmos arquivos (experimento E04). Este é um tópico que precisa de estudo próprio além do conteúdo da disciplina.

### 4.7 Segmentação de notas

Máquina de estados: silêncio, ataque, nota ativa, liberação. A nota é confirmada quando energia, frequência e periodicidade ficam consistentes por alguns quadros. Nota repetida da mesma altura só é detectada por rearticulação (queda de energia ou novo ataque), porque a frequência não muda.

**Onde entra:** transforma a curva de frequência por janela em eventos (nota, início, duração), que é o que o reconhecedor recebe. Responde à pergunta do enunciado sobre nota sustentada × nota repetida. O instante de início vem da energia e é confirmado depois, pois o estimador só estabiliza alguns quadros depois do ataque. Também exige estudo próprio (detecção de onset).

### 4.8 Comparação com o repertório

- **Absoluta (flauta):** notas MIDI e razões de duração. Cada duração é dividida pela duração média, tanto na execução quanto na canção, e as razões são comparadas com uma tolerância. Assim o reconhecimento não depende do andamento.
- **Relativa (assobio, extensão):** intervalos `12·log2(f[i+1]/f[i])` em semitons, que permitem tocar em outra altura.
- **Alinhamento:** associação um-para-um e monotônica entre eventos tocados e esperados, para que uma nota extra ou perdida não desloque o resto.

**Onde entra:** no reconhecedor, que decide entre canção reconhecida, nenhuma, ou divergência (com a posição da primeira nota errada, para o feedback do modo Aprender). No modo Tocar livre, o reconhecedor roda sobre o final do histórico de notas. A exigência de todos os eventos, na ordem, é o que evita aceitação por coincidência parcial.

## 5. Atendimento aos requisitos do projeto

### Requisitos mínimos comuns do enunciado

| # | Exigência | Como será atendida |
| --- | --- | --- |
| 1 | Sinal real adquirido pela equipe | Flauta doce gravada nos ensaios e tocada ao vivo na demonstração. |
| 2 | Frequência de amostragem identificada e justificada | Registro da taxa efetiva (44,1/48 kHz) e justificativa por Nyquist (seção 4.1). |
| 3 | Etapa explícita de PDS | Janelamento, filtragem, FFT/autocorrelação/YIN, segmentação. |
| 4 | Decisão/estimativa quantitativa | Frequência, nota, cents, durações e comparação com o repertório. |
| 5 | Saída ou resposta observável | Notas na tela, reação à canção correta, indicação de onde divergiu. |
| 6 | Testes e critérios de validação | Banco real, erros controlados e métricas (seção 6). |
| 7 | Embasamento teórico | Seção 4 e artigo. |
| 8 | Documentação de arquitetura, método, parâmetros, resultados, limitações e decisões | Este README, registro de sessões e artigo. |

### Perguntas de projeto do enunciado (Proposta 3)

| Pergunta | Resposta proposta |
| --- | --- |
| Reconhecimento absoluto ou relativo? | Absoluto (notas + durações proporcionais) para a flauta; relativo para o assobio, se adicionado. |
| Qual tolerância de afinação? | ±70 cents em torno da nota esperada (o Dó5 da flauta sai ~40 cents alto); medir o efeito de ±50 e ±35 na falsa aceitação. |
| Ritmo exato ou proporcional? | Proporcional, por razões de duração, com tolerância a medir. |
| Como voltar ao início após um erro? | Recomeçar do início da canção (modo Aprender). |
| Como distinguir nota sustentada de nota repetida? | Exigir nova articulação (queda de energia ou novo ataque). |
| Como evitar aceitação por coincidência parcial? | Exigir todos os eventos do começo, na ordem, com ritmo proporcional; repertório sem começos iguais; medir falsa aceitação. |

### Entregáveis

- [ ] Ficha de cadastro aprovada pelo professor (preenchida em `docs/proposta.pdf`, faltam os RAs).
- [x] Protótipo funcional ou demonstrador executável (jogo em Godot + serviço Python; ver seção 9).
- [ ] Código-fonte organizado e comentado.
- [ ] Dados de teste ou exemplos para reproduzir a demonstração.
- [ ] Artigo técnico (problema, fundamentação, arquitetura, métodos, experimentos, resultados, limitações, conclusões).
- [ ] Demonstração final ponta a ponta com critérios de validação.

### Requisitos funcionais do MVP

| ID | Requisito |
| --- | --- |
| RF01 | Capturar a flauta doce pelo microfone. |
| RF02 | Informar dispositivo e frequência de amostragem efetivamente usados. |
| RF03 | Estimar frequência fundamental e nota. |
| RF04 | Segmentar eventos musicais com início, fim e duração. |
| RF05 | Carregar canções do repertório (notas e durações relativas). |
| RF06 | Comparar execução e padrão por notas e ritmo proporcional. |
| RF07 | Reação inequívoca à canção correta; nenhuma à incorreta. |
| RF08 | Mostrar as notas reconhecidas e onde a execução divergiu. |
| RF09 | Reconhecer ausência de sinal confiável (silêncio, fala e ruído não viram notas). |
| RF10 | Gerar registros para validação. |

## 6. Validação

Até agora há só testes com sinal sintético (experimento E01 e os testes automáticos em `tests/`); os testes com a flauta real começam agora. As metas abaixo são pontos de partida a negociar depois da linha de base.

**Dados:** notas sustentadas da flauta (5 notas × 5 repetições × 2 executantes), transições, notas repetidas, sequências corretas, erros controlados (nota trocada, ritmo errado, canção pela metade, canção de mesmo começo), silêncio, fala e ruído. Áudios originais preservados; sessões de ajuste separadas das de avaliação final.

**Métricas**

| Aspecto | Medida |
| --- | --- |
| Nota | Acurácia e matriz de confusão. |
| Frequência | Erro em cents (mediana e P95), onde houver referência. |
| Eventos | Precisão, revocação e F1 com pareamento um-para-um. |
| Onset | Erro de início em ms (mediana e P95). |
| Canção | Taxa de reconhecimento, **taxa de falsa aceitação**, matriz de confusão entre canções. |
| Silêncio/ruído | Falsos eventos por minuto. |
| Latência | Tempo entre o evento acústico e o feedback visível. |

**Metas iniciais propostas:** reconhecimento ≥ 90%, falsa aceitação ≤ 5%, acurácia de nota ≥ 90%, F1 de eventos ≥ 0,85, P95 de latência ≤ 200 ms, no máximo 1 falso evento por minuto de silêncio.

**Experimentos:** (E01) sintéticos e silêncio; (E10) efeito do filtro (sem filtro × IIR × FIR) no mesmo áudio, em `experimentos/e10_filtros.py`; (E02) notas reais; (E03) repetição, legato e pausas; (E04) comparação de métodos de f0; (E05) janela, salto e confirmação; (E06) distância, intensidade e ruído; (E07) erros controlados; (E08) ponta a ponta ao vivo; (E09) pausa e captura interrompida.

## 7. Plano de trabalho

| Fase | Conteúdo | Saída |
| --- | --- | --- |
| 0 | Caracterizar a flauta, testar captura no Linux, definir repertório, submeter a ficha. | Ficha aprovada e ambiente funcionando. |
| 1 | Captura e frequência: tela de diagnóstico; FFT (Hann, com/sem interpolação) × autocorrelação. | Notas do repertório reconhecidas com confiança. |
| 2 | Eventos e ritmo: segmentação, nota sustentada × repetida, latência. | Sequência de notas com durações e qualidade medida. |
| 3 | Reconhecimento de canções e jogo: modos Aprender e Tocar livre, reação. | RF01–RF10 com evidência. |
| 4 | Validar e entregar: congelar configuração, experimentos, artigo, demonstração. | MVP e material acadêmico entregues. |
| 5 | Extensões opcionais: assobio, desafio rítmico. | Só com o núcleo pronto. |

**Situação:** as fases 1 a 3 estão implementadas e validadas com sinal sintético; falta repeti-las com a flauta real e fazer a fase 4.

**Riscos principais:** crescimento de escopo (o MVP é o filtro); resolução insuficiente da FFT nas notas graves (testar interpolação, janela maior, autocorrelação); falsa aceitação entre canções parecidas (par de mesmo começo no repertório); microfone diferente na demonstração (testar no equipamento real); melodias fora da extensão da flauta (repertório transposto por oitavas para Dó5–Lá6).

## 8. Distribuição de tarefas

| # | Tarefa | Responsável | Depende da flauta | Situação |
| --- | --- | --- | --- | --- |
| 1 | Ambiente: Godot, Blender e Krita; ambiente Python (`pytest`, `--simular`) | Gabriel e Elder | Não | Gabriel feito |
| 2 | Gravador de sessões com rótulos (WAV + metadados: canção, executante, condição) | Elder | Não | Feito |
| 3 | Serviço UDP que publica os eventos do jogo em JSON e recebe comandos | Gabriel | Não | Feito |
| 4 | Projeto Godot lendo os eventos | Gabriel | Não | Feito |
| 5 | Arte 3D própria: personagem e cenário modelados no Blender por script | Gabriel | Não | Feito |
| 6 | Filtro passa-faixa FIR/IIR e medição do efeito na estimativa de f0 | Elder | Não | Filtros feitos; falta medir com gravações |
| 7 | Perfil de parâmetros por instrumento (limiares e tolerâncias num só lugar) | Elder | Não | Pendente |
| 8 | Limiar de silêncio automático e aviso de ganho baixo ou saturado | Elder | Não | Feito (ganho automático) |
| 9 | Ferramentas de avaliação (reconhecimento, falsa aceitação, F1, matriz de confusão, latência P95) | Elder | Não | Pendente |
| 10 | Gravar as sessões com a flauta (notas sustentadas, 6 canções, erros, silêncio, fala, ruído) | Gabriel e Elder | Sim | Pendente |
| 11 | Calibrar afinação e limiares; conferir erro de oitava e notas rápidas | Elder | Sim | Pendente |
| 12 | Cena 3D completa, reações das 6 canções, HUD e menu | Gabriel | Não | Feito |
| 13 | Áudio no jogo: referência do modo Aprender, sons de acerto e erro, microfone mudo durante o som | Gabriel | Não | Feito |
| 14 | Experimentos E02–E09 e métricas finais, em sessões separadas da calibração | Elder | Sim | Pendente |
| 15 | Integração da flauta com o jogo e ensaio com o microfone da apresentação | Gabriel e Elder | Sim | Pendente |
| 16 | Artigo: jogo, interface e arquitetura (Gabriel); fundamentação do PDS, métodos, experimentos, resultados e limitações (Elder); introdução e conclusões (juntos) | Gabriel e Elder | Parcial | Pendente |
| 17 | README e ficha finais (RAs, créditos) | Gabriel e Elder | Não | Em andamento |

## 9. Como rodar

Requisitos: Linux, Python 3.12, PortAudio (`libportaudio2`) e Godot 4.4 ou mais recente.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest                       # testes automáticos
.venv/bin/python experimentos/gerar_repertorio.py  # gera repertorio/*.json a partir dos MIDIs locais
```

**Jogo:** em um terminal, suba o serviço; depois abra a pasta `jogo/` no Godot e rode (F5).

```bash
PYTHONPATH=src .venv/bin/python -m ocarina_beat.servidor   # --mudo para não tocar sons
```

No menu, "Entrada: Demonstração (sem flauta)" faz o serviço simular a canção, para apresentar sem o instrumento.

**Gravar sessões rotuladas** (WAV + metadados em `dados/brutos/`, fora do Git):

```bash
PYTHONPATH=src .venv/bin/python -m ocarina_beat.gravador --tipo cancao --alvo epona_song --executante gabriel
PYTHONPATH=src .venv/bin/python -m ocarina_beat.gravador --tipo nota --alvo A5 --executante gabriel --segundos 8
PYTHONPATH=src .venv/bin/python -m ocarina_beat.gravador --tipo silencio --executante gabriel --condicao "ventilador ligado"
PYTHONPATH=src .venv/bin/python -m ocarina_beat.gravador --listar
PYTHONPATH=src .venv/bin/python experimentos/e10_filtros.py   # compara os filtros nas gravações
```

**Terminal (sem Godot):**

```bash
PYTHONPATH=src .venv/bin/python -m ocarina_beat.diagnostico --segundos 15   # nível, frequência e nota em tempo real
PYTHONPATH=src .venv/bin/python -m ocarina_beat.cli livre                   # tocar livre pelo microfone
PYTHONPATH=src .venv/bin/python -m ocarina_beat.cli aprender epona_song     # aprender uma canção
PYTHONPATH=src .venv/bin/python -m ocarina_beat.cli livre --simular epona_song  # sem microfone
```

**Estrutura**

| Pasta | Conteúdo |
| --- | --- |
| `src/ocarina_beat/` | Captura, estimadores de f0, segmentador, reconhecedor, lógica do jogo, sons, serviço UDP e CLI. |
| `tests/` | Testes automáticos (`pytest`). |
| `experimentos/` | Experimentos (E01) e gerador do repertório. |
| `jogo/` | Projeto Godot: cena, personagem, cenário, reações, HUD, menu e a ponte com o Python. |
| `docs/` | Enunciado e ficha de proposta. |
