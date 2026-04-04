export const ribbonVertexShader = /* glsl */ `
precision mediump float;

uniform float uTime;
uniform vec2 uMouse;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vWorldPosition;
varying float vElevation;

vec3 displace(vec3 pos) {
  vec3 p = pos;
  p.z += sin(pos.x * 0.5 + uTime * 0.3) * 1.5;
  p.z += cos(pos.x * 0.3 + pos.y * 0.2 + uTime * 0.2) * 1.0;
  p.z += sin(pos.x * 0.8 - uTime * 0.15) * 0.5;
  p.z += cos(pos.y * 0.4 + uTime * 0.25) * 0.8;

  float twist = sin(pos.x * 0.2 + uTime * 0.1) * 0.5;
  float ct = cos(twist);
  float st = sin(twist);
  float newY = p.y * ct - p.z * st;
  float newZ = p.y * st + p.z * ct;
  p.y = newY;
  p.z = newZ;

  p.x += uMouse.x * 0.2;
  p.y += uMouse.y * 0.15;
  return p;
}

void main() {
  vUv = uv;
  vec3 displaced = displace(position);
  vElevation = displaced.z;
  vWorldPosition = (modelMatrix * vec4(displaced, 1.0)).xyz;

  float epsilon = 0.01;
  vec3 neighborX = displace(position + vec3(epsilon, 0.0, 0.0));
  vec3 neighborY = displace(position + vec3(0.0, epsilon, 0.0));
  vec3 tangentX = normalize(neighborX - displaced);
  vec3 tangentY = normalize(neighborY - displaced);
  vNormal = normalize(normalMatrix * normalize(cross(tangentX, tangentY)));

  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
}
`;

export const ribbonFragmentShader = /* glsl */ `
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
  float gradientT = clamp(vUv.x + sin(uTime * 0.08) * 0.15, 0.0, 1.0);
  vec3 color = mix(uColorA, uColorB, smoothstep(0.0, 0.5, gradientT));
  color = mix(color, uColorC, smoothstep(0.5, 1.0, gradientT));

  vec3 normal = normalize(vNormal);
  vec3 lightDir = normalize(vec3(0.5, 0.5, 0.5));
  float diff = max(dot(normal, lightDir), 0.0);
  color *= 0.4 + diff * 0.6;

  vec3 viewDir = normalize(cameraPosition - vWorldPosition);
  vec3 halfDir = normalize(lightDir + viewDir);
  float spec = pow(max(dot(normal, halfDir), 0.0), 32.0);
  color += vec3(1.0) * spec * 0.5;

  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
  color += fresnel * uColorB * 0.3;

  float fiber = sin(vUv.y * 200.0 + vUv.x * 30.0 + vElevation * 10.0) * 0.02;
  color += fiber;

  float alpha = smoothstep(0.0, 0.08, vUv.y) * smoothstep(1.0, 0.92, vUv.y);
  alpha *= 0.9 + fresnel * 0.1;

  gl_FragColor = vec4(clamp(color, 0.0, 1.0), alpha);
}
`;
