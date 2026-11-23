extends CanvasLayer
## HUD no estilo da referência: título no canto, sequência da canção (modo Aprender) ou
## histórico (modo livre), barra inferior com DÓ RÉ MI FÁ SOL LÁ SI e a nota reconhecida.
## A main.gd só chama os métodos públicos (titulo, nota, silencio, nivel, sequencia, progresso, mensagem, ajuda).

const AMBAR := Color("E9A93A")
const CREME := Color("F3E9D8")
const PAINEL := Color(0.10, 0.14, 0.21, 0.78)
const VERDE := Color("8DE0A0")
const VERMELHO := Color("E07A5F")
const SOLFEJO := {"C": "DÓ", "D": "RÉ", "E": "MI", "F": "FÁ", "G": "SOL", "A": "LÁ", "B": "SI"}
const ORDEM := ["C", "D", "E", "F", "G", "A", "B"]

var _fonte_titulo: SystemFont
var _lbl_titulo: Label
var _lbl_sub: Label
var _lbl_ajuda: Label
var _lbl_reconhecida: Label
var _lbl_msg: Label
var _notas_barra := {}  # letra -> {rotulo, ponto}
var _fundo_destaque: Panel
var _linha_seq: HBoxContainer
var _medidor: ProgressBar
var _seq: Array = []  # nomes das notas da canção (modo aprender) ou histórico (livre)
var _modo_aprender := false
var _tocadas := 0
var _tween_msg: Tween


func _ready() -> void:
	_fonte_titulo = SystemFont.new()
	_fonte_titulo.font_names = PackedStringArray(["Noto Serif", "DejaVu Serif", "Liberation Serif", "serif"])
	_fonte_titulo.font_weight = 700
	_montar_titulo()
	_montar_barra()
	_montar_sequencia()
	_montar_mensagem()


# ---------- API usada pela main.gd ----------
func titulo(sub: String) -> void:
	_lbl_sub.text = sub


func ajuda(txt: String) -> void:
	_lbl_ajuda.text = txt


func nota(nome: String) -> void:
	var letra := nome.substr(0, 1)
	var sustenido := nome.contains("#")
	var solf: String = SOLFEJO.get(letra, nome) + ("♯" if sustenido else "")
	_lbl_reconhecida.text = solf
	for l in _notas_barra:
		var item: Dictionary = _notas_barra[l]
		var ativo: bool = l == letra
		item.rotulo.text = SOLFEJO[l] + ("♯" if ativo and sustenido else "")
		item.rotulo.add_theme_color_override("font_color", Color("1B2433") if ativo else CREME)
		item.ponto.modulate = AMBAR if ativo else Color(CREME, 0.7)
		item.ponto.scale = Vector2.ONE * (1.6 if ativo else 1.0)
	var alvo: Label = _notas_barra[letra].rotulo if _notas_barra.has(letra) else null
	if alvo:
		_fundo_destaque.visible = true
		await get_tree().process_frame  # garante o layout antes de posicionar o destaque
		var r := alvo.get_global_rect()
		var t := create_tween().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		t.tween_property(_fundo_destaque, "global_position", r.position - Vector2(14, 4), 0.12)
		_fundo_destaque.size = r.size + Vector2(28, 8)
	if not _modo_aprender:
		_seq.append(solf)
		if _seq.size() > 8:
			_seq.pop_front()
		_desenhar_sequencia()


func silencio() -> void:
	_lbl_reconhecida.text = "—"


func nivel(v: float) -> void:
	_medidor.value = v


## modo aprender: notas da canção; [] volta ao histórico do modo livre
func sequencia(nomes: Array) -> void:
	_modo_aprender = nomes.size() > 0
	_seq = []
	for n in nomes:
		_seq.append(SOLFEJO.get(String(n).substr(0, 1), n) + ("♯" if String(n).contains("#") else ""))
	_tocadas = 0
	_desenhar_sequencia()


func progresso(tocadas: int) -> void:
	_tocadas = tocadas
	_desenhar_sequencia()


func mensagem(txt: String, tipo := "info") -> void:
	_lbl_msg.text = txt
	_lbl_msg.add_theme_color_override("font_color", VERDE if tipo == "ok" else (VERMELHO if tipo == "erro" else CREME))
	if _tween_msg and _tween_msg.is_valid():
		_tween_msg.kill()
	_lbl_msg.modulate.a = 1.0
	_lbl_msg.scale = Vector2.ONE * 1.15
	_tween_msg = create_tween()
	_tween_msg.tween_property(_lbl_msg, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_tween_msg.tween_interval(2.5)
	_tween_msg.tween_property(_lbl_msg, "modulate:a", 0.0, 0.6)


# ---------- construção ----------
func _caixa(cor: Color, raio := 18) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = cor
	s.set_corner_radius_all(raio)
	s.border_color = Color(CREME, 0.18)
	s.set_border_width_all(1)
	s.shadow_color = Color(0, 0, 0, 0.25)
	s.shadow_size = 8
	return s


func _rotulo(txt: String, tam: int, cor := CREME, fonte: Font = null) -> Label:
	var l := Label.new()
	l.text = txt
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", cor)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.45))
	l.add_theme_constant_override("shadow_offset_y", 2)
	if fonte:
		l.add_theme_font_override("font", fonte)
	return l


func _montar_titulo() -> void:
	var caixa := VBoxContainer.new()
	caixa.position = Vector2(36, 26)
	add_child(caixa)
	_lbl_titulo = _rotulo("❦  OCARINA BEAT", 34, CREME, _fonte_titulo)
	caixa.add_child(_lbl_titulo)
	var it := SystemFont.new()
	it.font_names = _fonte_titulo.font_names
	it.font_italic = true
	_lbl_sub = _rotulo("Prática musical", 22, Color(CREME, 0.9), it)
	caixa.add_child(_lbl_sub)
	_lbl_ajuda = _rotulo("", 14, Color(CREME, 0.75))
	_lbl_ajuda.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_lbl_ajuda.position = Vector2(-330, 26)
	_lbl_ajuda.size = Vector2(300, 200)
	_lbl_ajuda.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	add_child(_lbl_ajuda)


func _montar_barra() -> void:
	var painel := PanelContainer.new()
	painel.add_theme_stylebox_override("panel", _caixa(PAINEL))
	painel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	painel.custom_minimum_size = Vector2(1060, 96)
	painel.position = Vector2(-530, -122)
	add_child(painel)
	var linha := HBoxContainer.new()
	linha.add_theme_constant_override("separation", 0)
	painel.add_child(linha)

	# trilho com as 7 notas
	var trilho := Control.new()
	trilho.custom_minimum_size = Vector2(720, 96)
	linha.add_child(trilho)
	var risco := ColorRect.new()
	risco.color = Color(CREME, 0.35)
	risco.position = Vector2(60, 66)
	risco.size = Vector2(600, 2)
	trilho.add_child(risco)
	_fundo_destaque = Panel.new()
	var sd := _caixa(Color(AMBAR, 0.92), 14)
	sd.border_color = Color("FFD58A")
	_fundo_destaque.add_theme_stylebox_override("panel", sd)
	_fundo_destaque.visible = false
	trilho.add_child(_fundo_destaque)
	for i in ORDEM.size():
		var x := 60.0 + 600.0 * i / (ORDEM.size() - 1)
		var r := _rotulo(SOLFEJO[ORDEM[i]], 26, CREME, _fonte_titulo)
		r.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		r.position = Vector2(x - 40, 14)
		r.size = Vector2(80, 36)
		trilho.add_child(r)
		var p := Panel.new()
		var sp := StyleBoxFlat.new()
		sp.bg_color = Color.WHITE
		sp.set_corner_radius_all(6)
		p.add_theme_stylebox_override("panel", sp)
		p.size = Vector2(10, 10)
		p.pivot_offset = Vector2(5, 5)
		p.position = Vector2(x - 5, 62)
		p.modulate = Color(CREME, 0.7)
		trilho.add_child(p)
		_notas_barra[ORDEM[i]] = {"rotulo": r, "ponto": p}

	var sep := ColorRect.new()
	sep.color = Color(CREME, 0.25)
	sep.custom_minimum_size = Vector2(1, 60)
	sep.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	linha.add_child(sep)

	# nota reconhecida + medidor do microfone
	var dir := HBoxContainer.new()
	dir.custom_minimum_size = Vector2(330, 96)
	dir.alignment = BoxContainer.ALIGNMENT_CENTER
	dir.add_theme_constant_override("separation", 14)
	linha.add_child(dir)
	dir.add_child(_rotulo("Nota reconhecida:", 20))
	_lbl_reconhecida = _rotulo("—", 34, AMBAR, _fonte_titulo)
	_lbl_reconhecida.custom_minimum_size = Vector2(80, 0)
	dir.add_child(_lbl_reconhecida)
	_medidor = ProgressBar.new()
	_medidor.fill_mode = ProgressBar.FILL_BOTTOM_TO_TOP
	_medidor.show_percentage = false
	_medidor.max_value = 1.0
	_medidor.custom_minimum_size = Vector2(8, 54)
	_medidor.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var fundo := StyleBoxFlat.new()
	fundo.bg_color = Color(CREME, 0.15)
	fundo.set_corner_radius_all(4)
	var cheio := StyleBoxFlat.new()
	cheio.bg_color = AMBAR
	cheio.set_corner_radius_all(4)
	_medidor.add_theme_stylebox_override("background", fundo)
	_medidor.add_theme_stylebox_override("fill", cheio)
	dir.add_child(_medidor)


func _montar_sequencia() -> void:
	_linha_seq = HBoxContainer.new()
	_linha_seq.alignment = BoxContainer.ALIGNMENT_CENTER
	_linha_seq.add_theme_constant_override("separation", 8)
	_linha_seq.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_linha_seq.position = Vector2(-530, -170)
	_linha_seq.size = Vector2(1060, 40)
	add_child(_linha_seq)


func _desenhar_sequencia() -> void:
	for c in _linha_seq.get_children():
		c.queue_free()
	for i in _seq.size():
		var feita := _modo_aprender and i < _tocadas
		var proxima := _modo_aprender and i == _tocadas
		var cor := Color(0.12, 0.17, 0.24, 0.72)
		if feita:
			cor = Color(0.25, 0.48, 0.32, 0.9)
		var chip := PanelContainer.new()
		var st := _caixa(cor, 12)
		st.content_margin_left = 12
		st.content_margin_right = 12
		st.content_margin_top = 4
		st.content_margin_bottom = 4
		if proxima:
			st.border_color = AMBAR
			st.set_border_width_all(2)
		chip.add_theme_stylebox_override("panel", st)
		var txt_cor := CREME if (feita or proxima or not _modo_aprender) else Color(CREME, 0.55)
		chip.add_child(_rotulo(_seq[i], 18, txt_cor))
		_linha_seq.add_child(chip)


func _montar_mensagem() -> void:
	_lbl_msg = _rotulo("", 36, CREME, _fonte_titulo)
	_lbl_msg.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_lbl_msg.position = Vector2(-500, 110)
	_lbl_msg.size = Vector2(1000, 60)
	_lbl_msg.pivot_offset = Vector2(500, 30)
	_lbl_msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_lbl_msg.add_theme_constant_override("outline_size", 8)
	_lbl_msg.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.5))
	add_child(_lbl_msg)
