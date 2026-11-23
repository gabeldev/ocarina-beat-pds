extends CanvasLayer
## Tela inicial e menus (mouse ou teclado).
## Telas: inicio (Aprender / Tocar livre / Entrada / Sair), cancoes (escolher a canção),
## pausa (ESC durante o jogo: Continuar / Ouvir de novo / Trocar canção / Menu inicial).

signal aprender(id: String)
signal livre
signal continuar
signal ouvir_de_novo
signal menu_inicial

const AMBAR := Color("E9A93A")
const CREME := Color("F3E9D8")
const PAINEL := Color(0.10, 0.14, 0.21, 0.82)

var usar_microfone := true  # false = demonstração (o serviço simula a canção)
var tela := "inicio"
var _cancoes: Array = []
var _aprendidas: Array = []
var _caixa: VBoxContainer
var _painel: PanelContainer
var _fundo: ColorRect
var _serif: SystemFont
var _serif_it: SystemFont


func _ready() -> void:
	layer = 2
	_serif = SystemFont.new()
	_serif.font_names = PackedStringArray(["Noto Serif", "DejaVu Serif", "Liberation Serif", "serif"])
	_serif.font_weight = 700
	_serif_it = SystemFont.new()
	_serif_it.font_names = _serif.font_names
	_serif_it.font_italic = true
	_fundo = ColorRect.new()
	_fundo.color = Color(0.05, 0.07, 0.1, 0.35)
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	_painel = PanelContainer.new()
	var st := StyleBoxFlat.new()
	st.bg_color = PAINEL
	st.set_corner_radius_all(22)
	st.border_color = Color(CREME, 0.2)
	st.set_border_width_all(1)
	st.shadow_color = Color(0, 0, 0, 0.35)
	st.shadow_size = 16
	st.set_content_margin_all(34)
	_painel.add_theme_stylebox_override("panel", st)
	_painel.set_anchors_preset(Control.PRESET_CENTER_LEFT)
	_painel.position = Vector2(80, -250)
	_painel.custom_minimum_size = Vector2(420, 0)
	add_child(_painel)
	_caixa = VBoxContainer.new()
	_caixa.add_theme_constant_override("separation", 12)
	_painel.add_child(_caixa)
	mostrar("inicio")


func definir_cancoes(lista: Array) -> void:
	_cancoes = lista
	if visible and tela == "cancoes":
		mostrar("cancoes")


func definir_aprendidas(lista: Array) -> void:
	_aprendidas = lista
	if visible and tela == "cancoes":
		mostrar("cancoes")


func mostrar(qual: String) -> void:
	tela = qual
	visible = true
	for c in _caixa.get_children():
		c.queue_free()
	match qual:
		"inicio":
			_titulo("❦  OCARINA BEAT", "Toque e veja a clareira responder")
			_botao("Aprender uma canção", func(): mostrar("cancoes"))
			_botao("Tocar livre", func(): _fechar(); livre.emit())
			_botao(_texto_entrada(), _trocar_entrada)
			_botao("Sair", func(): get_tree().quit())
		"cancoes":
			_titulo("Aprender", "Escolha uma canção")
			for c in _cancoes:
				var marca := "  ✓" if _aprendidas.has(c.id) else ""
				var id: String = c.id
				_botao("%s%s" % [c.nome, marca], func(): _fechar(); aprender.emit(id))
			_botao("‹  Voltar", func(): mostrar("inicio"), true)
		"pausa":
			_titulo("Pausa", "")
			_botao("Continuar", func(): _fechar(); continuar.emit())
			_botao("Ouvir a canção de novo", func(): _fechar(); ouvir_de_novo.emit())
			_botao("Trocar de canção", func(): mostrar("cancoes"))
			_botao("Menu inicial", func(): mostrar("inicio"); menu_inicial.emit())
	await get_tree().process_frame
	var primeiro := _caixa.get_children().filter(func(n): return n is Button)
	if primeiro.size() > 0:
		primeiro[0].grab_focus()


func _fechar() -> void:
	visible = false


func _texto_entrada() -> String:
	return "Entrada: " + ("Microfone" if usar_microfone else "Demonstração (sem flauta)")


func _trocar_entrada() -> void:
	usar_microfone = not usar_microfone
	mostrar("inicio")


func _titulo(txt: String, sub: String) -> void:
	var t := Label.new()
	t.text = txt
	t.add_theme_font_override("font", _serif)
	t.add_theme_font_size_override("font_size", 40)
	t.add_theme_color_override("font_color", CREME)
	_caixa.add_child(t)
	if sub != "":
		var s := Label.new()
		s.text = sub
		s.add_theme_font_override("font", _serif_it)
		s.add_theme_font_size_override("font_size", 20)
		s.add_theme_color_override("font_color", Color(CREME, 0.8))
		_caixa.add_child(s)
	var esp := Control.new()
	esp.custom_minimum_size = Vector2(0, 10)
	_caixa.add_child(esp)


func _estilo(cor: Color, borda: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = cor
	s.set_corner_radius_all(14)
	s.border_color = borda
	s.set_border_width_all(2)
	s.content_margin_left = 20
	s.content_margin_right = 20
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	return s


func _botao(txt: String, acao: Callable, discreto := false) -> void:
	var b := Button.new()
	b.text = txt
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.add_theme_font_override("font", _serif)
	b.add_theme_font_size_override("font_size", 18 if discreto else 22)
	b.add_theme_color_override("font_color", CREME)
	b.add_theme_color_override("font_hover_color", Color("1B2433"))
	b.add_theme_color_override("font_focus_color", Color("1B2433"))
	b.add_theme_color_override("font_pressed_color", Color("1B2433"))
	b.add_theme_stylebox_override("normal", _estilo(Color(1, 1, 1, 0.06), Color(CREME, 0.15)))
	b.add_theme_stylebox_override("hover", _estilo(AMBAR, Color("FFD58A")))
	b.add_theme_stylebox_override("focus", _estilo(AMBAR, Color("FFD58A")))
	b.add_theme_stylebox_override("pressed", _estilo(AMBAR.darkened(0.15), Color("FFD58A")))
	b.pressed.connect(acao)
	_caixa.add_child(b)
