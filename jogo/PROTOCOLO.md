# Protocolo Python ↔ Godot

O serviço Python (`python -m ocarina_beat.servidor`) roda o PDS e o jogo. A interface só troca mensagens
JSON por UDP local, uma mensagem por datagrama, UTF-8.

| Sentido | Endereço |
| --- | --- |
| Python → Godot (eventos) | `127.0.0.1:9000` |
| Godot → Python (comandos) | `127.0.0.1:9001` |

Rodando o serviço: `PYTHONPATH=src .venv/bin/python -m ocarina_beat.servidor` (portas mudam com `--eventos` e `--comandos`).
No Godot, adicione `jogo/ponte.gd` como Autoload chamado `Ponte`; ele já converte cada evento num sinal.

## Comandos (Godot → Python)

| `cmd` | Campos | Efeito |
| --- | --- | --- |
| `livre` | | Modo Tocar livre. |
| `aprender` | `id` | Modo Aprender com a canção `id`. |
| `simular` | `id`, `bpm` (100), `ruido` (0) | Toca a canção sintetizada como se fosse o microfone (para testar sem flauta). Usa o modo atual. |
| `microfone` | `dispositivo` (opcional) | Passa a ouvir o microfone. |
| `parar` | | Para de ouvir. |
| `ouvir` | `id` (opcional: canção atual), `bpm` (100) | Toca a canção de referência pelo alto-falante. O microfone fica mudo enquanto isso. |
| `sons` | `ativo` (true/false) | Liga ou desliga os sons do jogo (referência, canção reconhecida, sucesso, erro). |
| `estado` | | Pede o evento `estado`. |
| `cancoes` | | Pede o evento `cancoes`. |
| `sair` | | Encerra o serviço. |

## Eventos (Python → Godot)

Todos têm `tipo`. Tempos `t` em segundos desde o início da fonte de áudio.

| `tipo` | Campos | Quando |
| --- | --- | --- |
| `estado` | `modo`, `alvo`, `instrumento`, `ouvindo`, `microfone`, `ganho_automatico`, `sons`, `aprendidas` | Ao iniciar e quando algo muda. |
| `cancoes` | `lista`: `[{id, nome, notas, beats, reconhecer_primeiras}]` | Resposta a `cancoes`. |
| `nivel` | `t`, `dbfs`, `midi`, `nome` | ~20 vezes por segundo. `midi` e `nome` são `null` quando não há tom. Serve para animar o personagem. |
| `nota` | `t`, `midi`, `nome`, `cents` | Uma nota nova foi confirmada. |
| `reconhecida` | `t`, `id`, `nome`, `erro_ritmo` | Modo livre: o que foi tocado forma uma canção. |
| `progresso` | `t`, `tocadas`, `total` | Modo aprender: acertou mais uma nota. |
| `divergencia` | `t`, `motivo` (`nota` ou `ritmo`), `posicao`, `esperada`, `tocada` | Modo aprender: errou; recomeça do início. Se `motivo` é `ritmo`, vêm também `esperado_s` e `tocado_s`. |
| `completa` | `t`, `id`, `nome` | Modo aprender: terminou a canção. |
| `incompleta` | `t`, `tocadas`, `total` | Modo aprender: 6 s sem nova nota. |
| `fim_audio` | | A fonte simulada ou de arquivo acabou. |
| `ganho` | `volume` (0–1), `motivo` (`saturacao` ou `fraco`) | O serviço ajustou sozinho o volume do microfone do sistema. |
| `audio_inicio` | `som` (`referencia`, `cancao`, `sucesso` ou `erro`), `duracao` | O serviço começou a tocar um som. O microfone é ignorado até o fim dele (mais 0,3 s). |
| `audio_fim` | `som` | O som terminou. |
| `referencia` | `indice`, `nome` | Durante `ouvir` (som `referencia`) ou depois de uma canção reconhecida no modo livre (som `cancao`): a nota `indice` está soando agora. |
| `erro` | `mensagem` | Comando inválido (o serviço continua rodando). |

O som do jogo sai do serviço Python, não do Godot: só ele sabe quando silenciar o microfone. `--mudo` desliga os sons.

`posicao` começa em 0. Os nomes de nota usam a oitava científica (`A4` = 440 Hz); `#` indica sustenido.

## Testar sem flauta

```
PYTHONPATH=src .venv/bin/python -m ocarina_beat.servidor
# no Godot: Ponte.enviar("simular", {"id": "epona_song"})
```
