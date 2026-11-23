extends Panel
## Guia da flauta doce soprano germânica. Cada coluna representa T, 1, 2, 3, 4, 5, 6, 7.
## Os dois furinhos de cada par recebem sempre a posição do mesmo dedo.

const DEDILHADO := {
	"C5":  [1, 1, 1, 1, 1, 1, 1, 1],
	"D5":  [1, 1, 1, 1, 1, 1, 1, 0],
	"E5":  [1, 1, 1, 1, 1, 1, 0, 0],
	"F5":  [1, 1, 1, 1, 1, 0, 0, 0],
	"G5":  [1, 1, 1, 1, 0, 0, 0, 0],
	"A5":  [1, 1, 1, 0, 0, 0, 0, 0],
	"B5":  [1, 1, 0, 0, 0, 0, 0, 0],
	"C6":  [1, 0, 1, 0, 0, 0, 0, 0],
	"C#6": [0, 1, 1, 0, 0, 0, 0, 0],
	"D6":  [0, 0, 1, 0, 0, 0, 0, 0],
	"E6":  [0.5, 1, 1, 1, 1, 1, 0, 0],
	"F6":  [0.5, 1, 1, 1, 1, 0, 0, 0],
	"G6":  [0.5, 1, 1, 1, 0, 0, 0, 0],
	"A6":  [0.5, 1, 1, 0, 0, 0, 0, 0],
}
const ABERTOS := [0, 0, 0, 0, 0, 0, 0, 0]
const TAMANHO := Vector2(212, 452)
const EIXO := TAMANHO.x * 0.5
const ALTURAS := [209, 233, 257, 284, 308, 332, 370]
const TINTA := Color("1B2433")
const AMBAR := Color("E9A93A")
const CREME := Color("F3E9D8")
const MARFIM := Color("FFF1D6")
const SULCO := Color("836D54")
# Raio e altura ao longo do instrumento, do bico estreito até o pé alargado.
const PERFIL := [
	Vector2(9, 91), Vector2(10, 93), Vector2(11, 108), Vector2(15, 119),
	Vector2(19, 128), Vector2(20, 134), Vector2(20, 172), Vector2(19, 180),
	Vector2(20, 184), Vector2(21, 186), Vector2(21, 190), Vector2(17, 194),
	Vector2(18, 205), Vector2(16, 320), Vector2(15, 344), Vector2(18, 347),
	Vector2(18, 352), Vector2(15, 355), Vector2(15, 371), Vector2(17, 384),
	Vector2(21, 393), Vector2(22, 397), Vector2(22, 401), Vector2(19, 404),
]

var _textura := GradientTexture1D.new()
var _nome := ""
var _solfejo := ""
var _oitava := ""
var _referencia := false
var _cobertura := PackedFloat32Array(ABERTOS)
var _transicao: Tween


func _ready() -> void:
	var gradiente := Gradient.new()
	gradiente.offsets = PackedFloat32Array([0.0, 0.12, 0.34, 0.56, 0.80, 1.0])
	gradiente.colors = PackedColorArray([
		Color("AE9776"), Color("DDC8A7"), Color("FFF7E5"),
		Color("F7E8CA"), Color("DDC6A3"), Color("AD9373"),
	])
	_textura.gradient = gradiente


func mostrar_nota(nome: String, solfejo: String, referencia: bool, animar: bool) -> void:
	_referencia = referencia
	queue_redraw()
	if nome == _nome and animar:
		return
	_nome = nome
	_solfejo = solfejo
	_oitava = nome.substr(2 if nome.contains("#") else 1)
	var destino := PackedFloat32Array(DEDILHADO.get(nome, ABERTOS))
	if _transicao:
		_transicao.kill()
	if animar and DEDILHADO.has(nome):
		# Em caso de notas rápidas, parte da cobertura que já aparece na tela.
		_transicao = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		_transicao.tween_method(_interpolar.bind(_cobertura.duplicate(), destino), 0.0, 1.0, 0.14)
	else:
		_cobertura = destino


func _interpolar(peso: float, origem: PackedFloat32Array, destino: PackedFloat32Array) -> void:
	for i in _cobertura.size():
		_cobertura[i] = lerpf(origem[i], destino[i], peso)
	queue_redraw()


func _draw() -> void:
	var fonte := ThemeDB.fallback_font
	draw_string(fonte, Vector2(0, 25), "Referência" if _referencia else "Próxima nota",
			HORIZONTAL_ALIGNMENT_CENTER, TAMANHO.x, 15, CREME)
	var serif := get_theme_font("font")
	var largura := serif.get_string_size(_solfejo, HORIZONTAL_ALIGNMENT_LEFT, -1, 36).x
	var largura_oitava := serif.get_string_size(_oitava, HORIZONTAL_ALIGNMENT_LEFT, -1, 19).x
	var x := EIXO - (largura + 3 + largura_oitava) * 0.5
	draw_string(serif, Vector2(x, 66), _solfejo, HORIZONTAL_ALIGNMENT_LEFT, -1, 36, CREME)
	draw_string(serif, Vector2(x + largura + 3, 54), _oitava, HORIZONTAL_ALIGNMENT_LEFT, -1, 19, AMBAR)
	_desenhar_corpo()

	var polegar := Vector2(50, ALTURAS[0])
	draw_dashed_line(polegar + Vector2(12, 0), Vector2(EIXO - 20, polegar.y), Color(CREME, 0.6), 1, 3)
	_furo(polegar, 7.5, _cobertura[0])
	draw_string(fonte, Vector2(5, polegar.y + 24), "Polegar", HORIZONTAL_ALIGNMENT_CENTER, 90, 13, CREME)
	for i in ALTURAS.size():
		var centro := Vector2(EIXO, ALTURAS[i])
		if i < 5:
			_furo(centro, 6.5 if i != 4 else 5.5, _cobertura[i + 1])
		else:
			_furo(centro + Vector2(-5, 0), 5.3, _cobertura[i + 1])
			_furo(centro + Vector2(7, 0), 3.5, _cobertura[i + 1])
		draw_string(fonte, centro + Vector2(30, 5), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, CREME)

	draw_line(Vector2(20, 415), Vector2(TAMANHO.x - 20, 415), Color(CREME, 0.20))
	if not DEDILHADO.has(_nome):
		draw_string(fonte, Vector2(0, 438), "posição não cadastrada", HORIZONTAL_ALIGNMENT_CENTER, TAMANHO.x, 14, CREME)
	elif DEDILHADO[_nome][0] == 0.5:
		_furo(Vector2(35, 433), 5, 0.5)
		draw_string(fonte, Vector2(48, 438), "Polegar entreaberto", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, CREME)
	else:
		_furo(Vector2(33, 433), 5, 0)
		draw_string(fonte, Vector2(45, 438), "aberto", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, CREME)
		_furo(Vector2(112, 433), 5, 1)
		draw_string(fonte, Vector2(124, 438), "tampado", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, CREME)


func _desenhar_corpo() -> void:
	var contorno := PackedVector2Array()
	for p: Vector2 in PERFIL:
		contorno.append(Vector2(EIXO - p.x, p.y))
	for i in range(PERFIL.size() - 1, -1, -1):
		var p: Vector2 = PERFIL[i]
		contorno.append(Vector2(EIXO + p.x, p.y))
	var uv := PackedVector2Array()
	for p in contorno:
		uv.append(Vector2(inverse_lerp(EIXO - 22, EIXO + 22, p.x), 0.5))
	draw_polygon(contorno, PackedColorArray([Color.WHITE]), uv, _textura)
	contorno.append(contorno[0])
	draw_polyline(contorno, Color("BEA786"), 1.2, true)

	# Canal de sopro, janela escura e rampa biselada do lábio.
	draw_line(Vector2(EIXO - 8, 93), Vector2(EIXO + 8, 93), SULCO, 2, true)
	draw_rect(Rect2(EIXO - 9, 130, 18, 8), Color("554839"))
	draw_colored_polygon(PackedVector2Array([
		Vector2(EIXO - 9, 138), Vector2(EIXO + 9, 138),
		Vector2(EIXO + 7, 154), Vector2(EIXO - 7, 154),
	]), Color("CBB492"))
	draw_line(Vector2(EIXO - 9, 138), Vector2(EIXO + 9, 138), MARFIM, 1.6, true)
	_anel(186, 21)
	_anel(348, 18)
	_anel(397, 22)


func _anel(y: float, raio: float) -> void:
	# A curva acompanha o arredondado da emenda torneada.
	var arco := PackedVector2Array()
	for i in 17:
		var u := (i - 8.0) / 8.0
		arco.append(Vector2(EIXO + u * raio, y + 2.2 * (1.0 - u * u)))
	draw_polyline(arco, MARFIM, 1.7, true)
	for i in arco.size():
		arco[i].y += 3
	draw_polyline(arco, SULCO, 1.2, true)


func _furo(centro: Vector2, raio: float, cobertura: float) -> void:
	if cobertura > 0:
		draw_circle(centro, raio + 3, Color(AMBAR, 0.18 * cobertura), true, -1, true)
		draw_circle(centro, raio + 1.8, Color(AMBAR, 0.32 * cobertura), true, -1, true)
	# As metades escurecem em sequência. A 0,5 só a esquerda está preenchida.
	var direita := clampf(2 * cobertura - 1, 0, 1)
	draw_circle(centro, raio, MARFIM.lerp(TINTA, direita), true, -1, true)
	if cobertura > 0 and cobertura < 1:
		var metade := PackedVector2Array()
		for i in 21:
			var angulo := PI * (0.5 + i / 20.0)
			metade.append(centro + Vector2.from_angle(angulo) * raio)
		draw_colored_polygon(metade, MARFIM.lerp(TINTA, minf(2 * cobertura, 1)))
	draw_arc(centro, raio, 0, TAU, 40, SULCO.lerp(AMBAR, minf(1, cobertura * 2)), 1.6, true)
