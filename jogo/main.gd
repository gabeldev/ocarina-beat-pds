extends Node3D
## Cena principal: liga os eventos da Ponte (serviço Python) ao personagem e ao HUD.
## Teclas: L = modo livre | 1..6 = aprender a canção N | S = simular a canção atual
##         M = microfone | P = parar | ESC = sair

@onready var camera: Camera3D = $Camera
@onready var sol: DirectionalLight3D = $Sol
@onready var hud = $HUD
@onready var personagem = $Personagem

var _cancoes: Array = []
var _alvo: String = ""
var _modo: String = "livre"
var _conectado := false


func _ready() -> void:
	# câmera frontal em três quartos, enquadrando rosto, mãos e instrumento (brief)
	camera.position = Vector3(0.8, 0.95, 2.8)
	camera.look_at(Vector3(0, 0.45, 0))
	camera.fov = 40
	sol.rotation_degrees = Vector3(-28, 25, 0)  # sol baixo de entardecer

	Ponte.estado.connect(_ao_estado)
	Ponte.cancoes.connect(_ao_cancoes)
	Ponte.nota.connect(func(d): hud.nota(d.nome))
	Ponte.nivel.connect(_ao_nivel)
	Ponte.progresso.connect(func(d): hud.progresso(int(d.tocadas)))
	Ponte.divergencia.connect(_ao_divergencia)
	Ponte.completa.connect(func(d): _celebrar("%s completa!" % d.nome); hud.progresso(int(d.get("total", 999))))
	Ponte.reconhecida.connect(func(d): _celebrar("%s!" % d.nome))
	Ponte.incompleta.connect(func(d): hud.mensagem("Incompleta: %d de %d notas" % [d.tocadas, d.total], "erro"); hud.progresso(0))
	Ponte.erro.connect(func(d): hud.mensagem(d.mensagem, "erro"))
	hud.titulo("Aguardando o serviço Python…")
	_pedir_estado()


func _pedir_estado() -> void:
	# o serviço só anuncia o estado ao subir; pedimos até ele responder
	if _conectado:
		return
	Ponte.enviar("estado")
	Ponte.enviar("cancoes")
	await get_tree().create_timer(1.0).timeout
	_pedir_estado()


func _unhandled_key_input(ev: InputEvent) -> void:
	if not (ev is InputEventKey and ev.pressed and not ev.echo):
		return
	match ev.keycode:
		KEY_L: Ponte.enviar("livre")
		KEY_S: Ponte.enviar("simular", {"id": _id_atual(), "bpm": 100})
		KEY_M: Ponte.enviar("microfone")
		KEY_P: Ponte.enviar("parar")
		KEY_ESCAPE: get_tree().quit()
		_:
			var n: int = ev.keycode - KEY_1
			if n >= 0 and n < _cancoes.size():
				Ponte.enviar("aprender", {"id": _cancoes[n].id})


func _id_atual() -> String:
	if _alvo != "":
		return _alvo
	return _cancoes[0].id if _cancoes.size() > 0 else ""


func _cancao(id: String) -> Dictionary:
	for c in _cancoes:
		if c.id == id:
			return c
	return {}


# --- eventos ---
func _ao_cancoes(d: Dictionary) -> void:
	_cancoes = d.lista
	var linhas := ["L livre · S simular · M microfone · P parar"]
	for i in _cancoes.size():
		linhas.append("%d  %s" % [i + 1, _cancoes[i].nome])
	hud.ajuda("\n".join(linhas))
	_atualizar_modo()


func _ao_estado(d: Dictionary) -> void:
	_conectado = true
	_modo = d.modo
	_alvo = d.alvo if d.alvo != null else ""
	_atualizar_modo()


func _atualizar_modo() -> void:
	var c := _cancao(_alvo)
	if _modo == "aprender" and not c.is_empty():
		hud.titulo("Aprender · %s" % c.nome)
		hud.sequencia(c.notas)
	else:
		hud.titulo("Tocar livre")
		hud.sequencia([])


func _ao_nivel(d: Dictionary) -> void:
	# medidor: -60 dBFS (silêncio) a -15 dBFS (forte)
	hud.nivel(clampf((float(d.dbfs) + 60.0) / 45.0, 0.0, 1.0))
	if d.nome == null:
		hud.silencio()
	else:
		personagem.som()


func _ao_divergencia(d: Dictionary) -> void:
	var txt := "Esperava %s, tocou %s" % [d.esperada, d.tocada]
	if d.motivo == "ritmo":
		txt = "Ritmo diferente na nota %d" % (int(d.posicao) + 1)
	hud.mensagem(txt, "erro")
	hud.progresso(0)


func _celebrar(txt: String) -> void:
	hud.mensagem(txt, "ok")
	personagem.sucesso()
	var t := create_tween()
	t.tween_property(sol, "light_energy", 2.0, 0.15)
	t.tween_property(sol, "light_energy", 1.0, 0.8)
