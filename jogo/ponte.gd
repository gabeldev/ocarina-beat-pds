extends Node
## Ponte com o serviço Python (python -m ocarina_beat.servidor).
## Adicione este script como Autoload (Projeto > Configurações > Autoload) com o nome "Ponte".
## Exemplo de uso em qualquer cena:
##   Ponte.nota.connect(func(d): print(d.nome))
##   Ponte.reconhecida.connect(func(d): print("Tocou ", d.nome))
##   Ponte.enviar("simular", {"id": "epona_song"})   # sem flauta, para testar
##   Ponte.enviar("aprender", {"id": "epona_song"})

signal evento(tipo: String, dados: Dictionary)  ## todo evento, para quem quiser tratar tudo
signal nota(dados: Dictionary)          ## {midi, nome, cents, t}
signal nivel(dados: Dictionary)         ## {dbfs, midi, nome, t} ~20x por segundo
signal progresso(dados: Dictionary)     ## modo aprender: {tocadas, total}
signal divergencia(dados: Dictionary)   ## modo aprender: {motivo, posicao, esperada, tocada}
signal completa(dados: Dictionary)      ## modo aprender: {id, nome}
signal reconhecida(dados: Dictionary)   ## modo livre: {id, nome, erro_ritmo}
signal incompleta(dados: Dictionary)
signal estado(dados: Dictionary)        ## {modo, alvo, instrumento, ouvindo, aprendidas}
signal cancoes(dados: Dictionary)       ## {lista: [{id, nome, notas, beats, reconhecer_primeiras}]}
signal erro(dados: Dictionary)
signal audio_inicio(dados: Dictionary)  ## {som, duracao}: o serviço começou a tocar
signal audio_fim(dados: Dictionary)     ## {som}
signal referencia(dados: Dictionary)    ## {indice, nome}: nota da referência soando agora

const HOST := "127.0.0.1"
const PORTA_EVENTOS := 9000
const PORTA_COMANDOS := 9001

var _rx := PacketPeerUDP.new()
var _tx := PacketPeerUDP.new()


func _init() -> void:
	# portas podem ser trocadas por ambiente (útil para rodar duas instâncias)
	var p_ev := int(OS.get_environment("OCARINA_PORTA_EVENTOS")) if OS.has_environment("OCARINA_PORTA_EVENTOS") else PORTA_EVENTOS
	var p_cmd := int(OS.get_environment("OCARINA_PORTA_COMANDOS")) if OS.has_environment("OCARINA_PORTA_COMANDOS") else PORTA_COMANDOS
	_tx.set_dest_address(HOST, p_cmd)
	var e := _rx.bind(p_ev, HOST)
	if e != OK:
		push_error("Ponte: não consegui abrir a porta %d (já em uso?)" % p_ev)


func _process(_delta: float) -> void:
	while _rx.get_available_packet_count() > 0:
		var msg = JSON.parse_string(_rx.get_packet().get_string_from_utf8())
		if msg is Dictionary and msg.has("tipo"):
			_despachar(msg)


func _despachar(msg: Dictionary) -> void:
	var tipo: String = msg["tipo"]
	evento.emit(tipo, msg)
	if has_signal(tipo):
		emit_signal(tipo, msg)


## Envia um comando: livre, aprender {id}, simular {id, bpm, ruido}, microfone,
## parar, ouvir {id, bpm}, sons {ativo}, estado, cancoes, sair.
func enviar(cmd: String, extra: Dictionary = {}) -> void:
	var m := {"cmd": cmd}
	m.merge(extra)
	_tx.put_packet(JSON.stringify(m).to_utf8_buffer())
