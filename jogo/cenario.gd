extends Node3D
## Ajustes do cenário importado (modelos/cenario.glb):
## troca o material "Agua" pelo shader animado e faz a lanterna tremeluzir.

const AGUA := preload("res://agua.gdshader")

var _luz: OmniLight3D
var _energia_base := 1.0


func _ready() -> void:
	var agua := ShaderMaterial.new()
	agua.shader = AGUA
	for m in find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = m.mesh
		for i in mesh.get_surface_count():
			var mat := mesh.surface_get_material(i)
			if mat and mat.resource_name == "Agua":
				m.set_surface_override_material(i, agua)
	_luz = find_child("LuzLanterna", true, false) as OmniLight3D
	if _luz == null:  # o importador pode criar a luz como filho do nó com esse nome
		var no := find_child("LuzLanterna", true, false)
		if no:
			_luz = no.find_children("*", "OmniLight3D", true, false).front() if no.find_children("*", "OmniLight3D", true, false).size() else null
	if _luz:
		_luz.light_color = Color("FFB347")
		_luz.omni_range = 5.0
		_luz.shadow_enabled = true
		_energia_base = 2.5


var _reforco := 1.0


## Lanterna mais forte por um tempo (reação da Zelda's Lullaby).
func reforcar_lanterna(fator: float, segundos: float) -> void:
	var t := create_tween()
	t.tween_property(self, "_reforco", fator, 0.6)
	t.tween_interval(segundos)
	t.tween_property(self, "_reforco", 1.0, 1.5)


func _process(_dt: float) -> void:
	if _luz:
		var t := Time.get_ticks_msec() / 1000.0
		_luz.light_energy = _reforco * _energia_base * (0.9 + 0.06 * sin(t * 9.0) + 0.04 * sin(t * 23.0))
