extends Node3D
## Cena principal: menu -> jogo. Liga os eventos da Ponte (serviço Python) ao personagem,
## às reações da cena e ao HUD. Os sons saem do serviço Python (ele silencia o microfone).
## Teclas no jogo: ESC = pausa | R = ouvir de novo | S = simular a canção atual (teste sem flauta)

const POSE_JOGO := {"pos": Vector3(0.8, 0.95, 2.8), "alvo": Vector3(0, 0.45, 0)}
const RAIO_MENU := 4.2

@onready var camera: Camera3D = $Camera
@onready var sol: DirectionalLight3D = $Sol
@onready var hud = $HUD
@onready var menu = $Menu
@onready var reacoes = $Reacoes
@onready var personagem = $Personagem

var _cancoes: Array = []
var _alvo: String = ""
var _modo: String = "livre"
var _conectado := false
var _microfone_ativo := false
var _em_jogo := false
var _angulo_menu := 0.6


func _ready() -> void:
	camera.fov = 40
	sol.rotation_degrees = Vector3(-28, 25, 0)  # sol baixo de entardecer
	_posicionar_camera(1.0)

	Ponte.estado.connect(_ao_estado)
	Ponte.cancoes.connect(_ao_cancoes)
	Ponte.nota.connect(func(d): hud.nota(d.nome))
	Ponte.nivel.connect(_ao_nivel)
	Ponte.progresso.connect(func(d): hud.progresso(int(d.tocadas)))
	Ponte.divergencia.connect(_ao_divergencia)
	Ponte.completa.connect(func(d): _celebrar(d.id, "%s completa!" % d.nome); hud.progresso(999))
	Ponte.reconhecida.connect(_ao_reconhecida)
	Ponte.incompleta.connect(func(d): hud.mensagem("Incompleta: %d de %d notas" % [d.tocadas, d.total], "erro"); hud.progresso(0))
	Ponte.erro.connect(func(d): hud.mensagem(d.mensagem, "erro"))
	Ponte.referencia.connect(_ao_referencia)
	Ponte.audio_fim.connect(_ao_audio_fim)

	menu.aprender.connect(_iniciar_aprender)
	menu.livre.connect(_iniciar_livre)
	menu.continuar.connect(func(): hud.visible = true)
	menu.ouvir_de_novo.connect(func(): hud.visible = true; _ouvir())
	menu.menu_inicial.connect(_voltar_ao_menu)
	hud.visible = false
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


# ---------- câmera: gira devagar no menu, vai para a pose de jogo ao começar ----------
func _process(dt: float) -> void:
	if not _em_jogo:
		_angulo_menu += dt * 0.06
	_posicionar_camera(1.0 - exp(-dt * 2.5))


func _posicionar_camera(peso: float) -> void:
	var pos: Vector3
	var alvo: Vector3
	if _em_jogo:
		pos = POSE_JOGO.pos
		alvo = POSE_JOGO.alvo
	else:
		pos = Vector3(sin(_angulo_menu) * RAIO_MENU, 1.6, cos(_angulo_menu) * RAIO_MENU)
		alvo = Vector3(0, 0.8, 0)
	var destino := Transform3D(Basis(), pos).looking_at(alvo)
	camera.global_transform = camera.global_transform.interpolate_with(destino, peso)


# ---------- fluxo de jogo ----------
func _comecar() -> void:
	_em_jogo = true
	hud.visible = true
	if menu.usar_microfone and not _microfone_ativo:
		Ponte.enviar("microfone")
	elif not menu.usar_microfone:
		Ponte.enviar("parar")


func _iniciar_aprender(id: String) -> void:
	Ponte.enviar("aprender", {"id": id})
	_alvo = id
	_modo = "aprender"
	_atualizar_modo()
	_comecar()
	await get_tree().create_timer(0.6).timeout  # deixa a câmera chegar
	_ouvir()


func _iniciar_livre() -> void:
	Ponte.enviar("livre")
	_modo = "livre"
	_atualizar_modo()
	_comecar()
	if menu.usar_microfone:
		hud.mensagem("Toque uma canção na flauta", "info")
	else:
		hud.mensagem("Demonstração: tocando uma canção…", "info")
		await get_tree().create_timer(1.0).timeout
		Ponte.enviar("simular", {"id": _cancoes.pick_random().id, "bpm": 100})


func _ouvir() -> void:
	if _modo != "aprender" or _alvo == "":
		return
	hud.mensagem("Ouça a canção…", "info")
	Ponte.enviar("ouvir", {"id": _alvo, "bpm": 100})


func _ao_referencia(d: Dictionary) -> void:
	hud.destacar_referencia(int(d.indice))
	hud.nota(d.nome)


func _ao_reconhecida(d: Dictionary) -> void:
	_celebrar(d.id, "%s!" % d.nome)
	# a canção reconhecida vai tocar inteira: mostra as notas dela acendendo
	var c := _cancao(d.id)
	if not c.is_empty():
		hud.sequencia(c.notas)


func _ao_audio_fim(d: Dictionary) -> void:
	if d.som == "cancao":
		hud.destacar_referencia(-1)
		hud.silencio()
		_atualizar_modo()  # volta ao histórico do modo livre
		return
	if d.som != "referencia":
		return
	hud.destacar_referencia(-1)
	hud.silencio()
	if menu.usar_microfone:
		hud.mensagem("Sua vez!", "ok")
	else:
		hud.mensagem("Demonstração: tocando…", "info")
		Ponte.enviar("simular", {"id": _alvo, "bpm": 100})


func _voltar_ao_menu() -> void:
	_em_jogo = false
	hud.visible = false
	Ponte.enviar("parar")


func _unhandled_key_input(ev: InputEvent) -> void:
	if not (ev is InputEventKey and ev.pressed and not ev.echo) or not _em_jogo:
		return
	match ev.keycode:
		KEY_ESCAPE:
			hud.visible = false
			menu.mostrar("pausa")
		KEY_R: _ouvir()
		KEY_S: Ponte.enviar("simular", {"id": _alvo if _alvo != "" else _cancoes[0].id, "bpm": 100})


# ---------- eventos do serviço ----------
func _cancao(id: String) -> Dictionary:
	for c in _cancoes:
		if c.id == id:
			return c
	return {}


func _ao_cancoes(d: Dictionary) -> void:
	_cancoes = d.lista
	menu.definir_cancoes(_cancoes)
	hud.ajuda("ESC menu · R ouvir de novo")
	_atualizar_modo()


func _ao_estado(d: Dictionary) -> void:
	_conectado = true
	_microfone_ativo = d.get("microfone", false)
	menu.definir_aprendidas(d.aprendidas)


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


func _celebrar(id: String, txt: String) -> void:
	hud.mensagem(txt, "ok")
	personagem.sucesso()
	reacoes.reagir(id)
