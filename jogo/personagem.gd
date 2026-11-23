extends Node3D
## Controla as animações do personagem a partir do som (não do teclado):
## repouso (idle) -> erguer -> tocar (loop) -> abaixar -> repouso; "success" quando a canção fecha.
## Os clipes vêm de modelos/personagem.glb (idle, raise_ocarina, play_loop, lower_ocarina, success).

enum Estado { REPOUSO, TOCANDO, SUCESSO }

const SILENCIO_PARA_ABAIXAR_S := 1.5  # sem tom por esse tempo, guarda a ocarina

var estado := Estado.REPOUSO
var _anim: AnimationPlayer
var _ultimo_som := -100.0
var _tocar := "play_loop"  # o importador do Godot tira o sufixo "_loop" (vira "play")


func _ready() -> void:
	_anim = find_child("AnimationPlayer", true, false)
	if not _anim.has_animation(_tocar):
		_tocar = "play"
	for nome in ["idle", _tocar]:
		if _anim.has_animation(nome):
			_anim.get_animation(nome).loop_mode = Animation.LOOP_LINEAR
	_anim.animation_finished.connect(_ao_terminar)
	_anim.play("idle", 0.2)


func _agora() -> float:
	return Time.get_ticks_msec() / 1000.0


## Chamado a cada evento de nível com tom presente.
func som() -> void:
	_ultimo_som = _agora()
	if estado == Estado.REPOUSO:
		estado = Estado.TOCANDO
		_anim.play("raise_ocarina", 0.15)
		_anim.queue(_tocar)


func sucesso() -> void:
	estado = Estado.SUCESSO
	_anim.play("success", 0.1)


func _process(_dt: float) -> void:
	if estado == Estado.TOCANDO and _agora() - _ultimo_som > SILENCIO_PARA_ABAIXAR_S:
		estado = Estado.REPOUSO
		_anim.play("lower_ocarina", 0.15)
		_anim.queue("idle")


func _ao_terminar(nome: StringName) -> void:
	if nome == "success":
		# volta a tocar se ainda há som; senão, guarda a ocarina
		if _agora() - _ultimo_som < SILENCIO_PARA_ABAIXAR_S:
			estado = Estado.TOCANDO
			_anim.play(_tocar, 0.2)
		else:
			estado = Estado.REPOUSO
			_anim.play("lower_ocarina", 0.1)
			_anim.queue("idle")
