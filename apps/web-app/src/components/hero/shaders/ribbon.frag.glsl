precision mediump float;

uniform float uTime;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorC;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vWorldPosition;
varying float vElevation;

void main() {
  // Gradient with slow iridescence shift
  float gradientT = clamp(vUv.x + sin(uTime * 0.08) * 0.15, 0.0, 1.0);
  vec3 color = mix(uColorA, uColorB, smoothstep(0.0, 0.5, gradientT));
  color = mix(color, uColorC, smoothstep(0.5, 1.0, gradientT));

  // Diffuse lighting
  vec3 normal = normalize(vNormal);
  vec3 lightDir = normalize(vec3(0.5, 0.5, 0.5));
  float diff = max(dot(normal, lightDir), 0.0);
  float diffuse = 0.4 + diff * 0.6;

  // Specular (Blinn-Phong)
  vec3 viewDir = normalize(cameraPosition - vWorldPosition);
  vec3 halfDir = normalize(lightDir + viewDir);
  float spec = pow(max(dot(normal, halfDir), 0.0), 32.0);

  color *= diffuse;
  color += vec3(1.0) * spec * 0.5;

  // Fresnel edge glow
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
  color += fresnel * uColorB * 0.3;

  // Fiber texture
  float fiber = sin(vUv.y * 200.0 + vUv.x * 30.0 + vElevation * 10.0) * 0.02;
  color += fiber;

  // Alpha: soft edges
  float alpha = smoothstep(0.0, 0.08, vUv.y) * smoothstep(1.0, 0.92, vUv.y);
  alpha *= 0.9 + fresnel * 0.1;

  gl_FragColor = vec4(clamp(color, 0.0, 1.0), alpha);
}
