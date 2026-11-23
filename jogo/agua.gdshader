shader_type spatial;
// Água estilizada para o material "Agua" do cenário: cor que ondula, brilho de borda e reflexo do pôr do sol.

uniform vec4 cor_rasa : source_color = vec4(0.36, 0.62, 0.66, 1.0);
uniform vec4 cor_funda : source_color = vec4(0.13, 0.31, 0.37, 1.0);
uniform vec4 cor_reflexo : source_color = vec4(1.0, 0.72, 0.55, 1.0);
uniform float velocidade = 0.6;

varying vec3 pos_mundo;

void vertex() {
	pos_mundo = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = pos_mundo.xz;
	float t = TIME * velocidade;
	float onda = sin(p.x * 7.0 + t * 3.0) * 0.5 + sin((p.x + p.y) * 11.0 - t * 2.3) * 0.3 + sin(p.y * 5.0 + t) * 0.2;
	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = mix(cor_funda.rgb, cor_rasa.rgb, 0.5 + 0.3 * onda);
	ROUGHNESS = 0.12;
	SPECULAR = 0.8;
	// brilhos em faixas, como na referência
	float faixa = smoothstep(0.82, 0.98, onda);
	EMISSION = cor_reflexo.rgb * (fresnel * 0.35 + faixa * 0.25);
	NORMAL = normalize(NORMAL + vec3(onda * 0.04, 0.0, onda * 0.03));
}
