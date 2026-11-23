extends Node3D
## Reação visual de cada canção (tarefa 12). Tudo procedural: partículas, céu, sol e lanterna.
## main.gd chama reagir(id) quando a canção é reconhecida (livre) ou completada (aprender).

@export var ambiente: WorldEnvironment
@export var sol: DirectionalLight3D
@export var cenario: Node3D

var _textura_ponto: GradientTexture2D
var _ceu_original := {}
var _ocupado := false


func _ready() -> void:
	# sprite redondo e macio usado por todas as partículas
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	_textura_ponto = GradientTexture2D.new()
	_textura_ponto.gradient = g
	_textura_ponto.fill = GradientTexture2D.FILL_RADIAL
	_textura_ponto.fill_from = Vector2(0.5, 0.5)
	_textura_ponto.fill_to = Vector2(0.5, 0.0)
	_textura_ponto.width = 64
	_textura_ponto.height = 64
	var ceu: ProceduralSkyMaterial = ambiente.environment.sky.sky_material
	_ceu_original = {
		"top": ceu.sky_top_color, "horizonte": ceu.sky_horizon_color,
		"sol": sol.light_energy, "ambiente": ambiente.environment.ambient_light_energy,
		"neblina": ambiente.environment.fog_density, "cor_sol": sol.light_color,
	}


func reagir(id: String) -> void:
	match id:
		"song_of_storms": _tempestade()
		"song_of_time": _noite()
		"epona_song": _vagalumes()
		"sarias_song": _folhas()
		"zeldas_lullaby": _lanterna()
		_: _explosao_dourada()


# ---------- reações ----------
func _tempestade() -> void:
	_mudar_ceu(Color(0.22, 0.24, 0.3), Color(0.42, 0.45, 0.5), 0.25, 0.35, 0.03, 7.0)
	var chuva := _particulas(Color(0.75, 0.85, 1.0, 0.55), 1800, 0.7, Vector3(0, 6, 0), 1.0)
	var m: ParticleProcessMaterial = chuva.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	m.emission_box_extents = Vector3(7, 0.5, 7)
	m.direction = Vector3(0.1, -1, 0)
	m.spread = 2.0
	m.initial_velocity_min = 14.0
	m.initial_velocity_max = 18.0
	m.gravity = Vector3(0, -9.8, 0)
	(chuva.draw_pass_1 as QuadMesh).size = Vector2(0.015, 0.35)
	(chuva.draw_pass_1.material as StandardMaterial3D).billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	_durar(chuva, 6.5)
	# dois relâmpagos
	var t := create_tween()
	for atraso in [1.2, 3.4]:
		t.tween_interval(atraso)
		t.tween_property(sol, "light_energy", 4.0, 0.04)
		t.tween_property(sol, "light_energy", 0.25, 0.25)


func _noite() -> void:
	_mudar_ceu(Color(0.05, 0.06, 0.18), Color(0.25, 0.22, 0.45), 0.15, 0.3, -1.0, 6.0)
	var aneis := _particulas(Color(0.65, 0.8, 1.0), 90, 3.0, Vector3(0, 0.7, 0), 2.0)
	var m: ParticleProcessMaterial = aneis.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
	m.emission_ring_axis = Vector3.UP
	m.emission_ring_radius = 1.1
	m.emission_ring_inner_radius = 1.0
	m.emission_ring_height = 0.05
	m.orbit_velocity_min = 0.25
	m.orbit_velocity_max = 0.3
	m.gravity = Vector3.ZERO
	m.scale_min = 0.04
	m.scale_max = 0.07
	_durar(aneis, 5.5)
	var estrelas := _particulas(Color(1, 1, 0.95), 120, 5.0, Vector3(0, 9, -10), 1.8)
	var e: ParticleProcessMaterial = estrelas.process_material
	e.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	e.emission_box_extents = Vector3(14, 4, 1)
	e.gravity = Vector3.ZERO
	e.scale_min = 0.05
	e.scale_max = 0.12
	_durar(estrelas, 5.0)


func _vagalumes() -> void:
	var v := _particulas(Color(0.85, 1.0, 0.45), 70, 5.0, Vector3(0, 0.9, 0), 2.0)
	var m: ParticleProcessMaterial = v.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	m.emission_box_extents = Vector3(3, 0.8, 2)
	m.gravity = Vector3(0, 0.05, 0)
	m.initial_velocity_min = 0.1
	m.initial_velocity_max = 0.3
	m.spread = 180.0
	m.turbulence_enabled = true
	m.turbulence_noise_strength = 2.0
	m.turbulence_noise_speed_random = 0.5
	m.scale_min = 0.03
	m.scale_max = 0.06
	_piscar(m)
	_durar(v, 8.0)


func _folhas() -> void:
	var f := _particulas(Color(0.55, 0.95, 0.4), 160, 2.5, Vector3(0, 0.1, 0), 1.6)
	var m: ParticleProcessMaterial = f.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
	m.emission_ring_axis = Vector3.UP
	m.emission_ring_radius = 0.9
	m.emission_ring_inner_radius = 0.6
	m.emission_ring_height = 0.1
	m.orbit_velocity_min = 0.4
	m.orbit_velocity_max = 0.6
	m.gravity = Vector3(0, 0.9, 0)
	m.scale_min = 0.03
	m.scale_max = 0.07
	_durar(f, 4.5)


func _lanterna() -> void:
	if cenario and cenario.has_method("reforcar_lanterna"):
		cenario.reforcar_lanterna(3.0, 5.0)
	var p := _particulas(Color(1.0, 0.72, 0.35), 110, 3.0, Vector3(0, 0.2, 0), 1.8)
	var m: ParticleProcessMaterial = p.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	m.emission_sphere_radius = 1.3
	m.gravity = Vector3(0, 0.4, 0)
	m.turbulence_enabled = true
	m.turbulence_noise_strength = 0.6
	m.scale_min = 0.03
	m.scale_max = 0.06
	_durar(p, 4.5)


func _explosao_dourada() -> void:
	var p := _particulas(Color(1.0, 0.85, 0.4), 200, 1.6, Vector3(0, 0.6, 0), 2.0)
	p.one_shot = true
	p.explosiveness = 0.9
	var m: ParticleProcessMaterial = p.process_material
	m.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	m.emission_sphere_radius = 0.2
	m.direction = Vector3.UP
	m.spread = 180.0
	m.initial_velocity_min = 1.5
	m.initial_velocity_max = 3.0
	m.gravity = Vector3(0, -1.5, 0)
	m.damping_min = 1.0
	m.damping_max = 2.0
	m.scale_min = 0.04
	m.scale_max = 0.08
	_durar(p, 0.2)


# ---------- utilidades ----------
func _particulas(cor: Color, quantidade: int, vida: float, pos: Vector3, brilho: float) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = quantidade
	p.lifetime = vida
	p.position = pos
	p.visibility_aabb = AABB(Vector3(-20, -20, -20), Vector3(40, 40, 40))
	var m := ParticleProcessMaterial.new()
	m.color = cor
	# entra e sai suave
	var curva := Curve.new()
	curva.add_point(Vector2(0, 0))
	curva.add_point(Vector2(0.15, 1))
	curva.add_point(Vector2(0.8, 1))
	curva.add_point(Vector2(1, 0))
	var ct := CurveTexture.new()
	ct.curve = curva
	m.scale_curve = ct
	p.process_material = m
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.billboard_keep_scale = true  # sem isso a escala das partículas é ignorada
	mat.vertex_color_use_as_albedo = true
	mat.albedo_texture = _textura_ponto
	mat.albedo_color = Color(brilho, brilho, brilho)  # >1 passa do limiar do glow
	quad.material = mat
	p.draw_pass_1 = quad
	add_child(p)
	p.emitting = true
	return p


func _durar(p: GPUParticles3D, segundos: float) -> void:
	await get_tree().create_timer(segundos).timeout
	if is_instance_valid(p):
		p.emitting = false
		await get_tree().create_timer(p.lifetime + 0.5).timeout
		if is_instance_valid(p):
			p.queue_free()


func _piscar(m: ParticleProcessMaterial) -> void:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 0))
	g.add_point(0.2, Color(1, 1, 1, 1))
	g.add_point(0.4, Color(1, 1, 1, 0.2))
	g.add_point(0.6, Color(1, 1, 1, 1))
	g.set_color(g.get_point_count() - 1, Color(1, 1, 1, 0))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	m.color_ramp = gt


## Muda céu, sol, luz ambiente e neblina e volta ao original depois de `dur` segundos.
func _mudar_ceu(topo: Color, horizonte: Color, energia_sol: float, ambiente_e: float, neblina: float, dur: float) -> void:
	if _ocupado:
		return
	_ocupado = true
	var ceu: ProceduralSkyMaterial = ambiente.environment.sky.sky_material
	var env := ambiente.environment
	var ida := create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE)
	ida.tween_property(ceu, "sky_top_color", topo, 1.2)
	ida.tween_property(ceu, "sky_horizon_color", horizonte, 1.2)
	ida.tween_property(sol, "light_energy", energia_sol, 1.2)
	ida.tween_property(env, "ambient_light_energy", ambiente_e, 1.2)
	if neblina >= 0.0:
		ida.tween_property(env, "fog_density", neblina, 1.2)
	await get_tree().create_timer(dur).timeout
	var volta := create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE)
	volta.tween_property(ceu, "sky_top_color", _ceu_original.top, 2.0)
	volta.tween_property(ceu, "sky_horizon_color", _ceu_original.horizonte, 2.0)
	volta.tween_property(sol, "light_energy", _ceu_original.sol, 2.0)
	volta.tween_property(env, "ambient_light_energy", _ceu_original.ambiente, 2.0)
	volta.tween_property(env, "fog_density", _ceu_original.neblina, 2.0)
	await volta.finished
	_ocupado = false
