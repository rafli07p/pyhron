precision mediump float;

uniform float uTime;
uniform vec2 uMouse;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vWorldPosition;
varying float vElevation;

vec3 displace(vec3 pos) {
  vec3 p = pos;

  // Layer 1: broad slow wave
  p.z += sin(pos.x * 0.5 + uTime * 0.3) * 1.5;
  // Layer 2: medium cross-wave
  p.z += cos(pos.x * 0.3 + pos.y * 0.2 + uTime * 0.2) * 1.0;
  // Layer 3: fast detail ripple
  p.z += sin(pos.x * 0.8 - uTime * 0.15) * 0.5;
  // Layer 4: Y-axis undulation
  p.z += cos(pos.y * 0.4 + uTime * 0.25) * 0.8;

  // Twist along X axis
  float twist = sin(pos.x * 0.2 + uTime * 0.1) * 0.5;
  float ct = cos(twist);
  float st = sin(twist);
  float newY = p.y * ct - p.z * st;
  float newZ = p.y * st + p.z * ct;
  p.y = newY;
  p.z = newZ;

  // Subtle mouse influence
  p.x += uMouse.x * 0.2;
  p.y += uMouse.y * 0.15;

  return p;
}

void main() {
  vUv = uv;

  vec3 displaced = displace(position);
  vElevation = displaced.z;
  vWorldPosition = (modelMatrix * vec4(displaced, 1.0)).xyz;

  // Normal recalculation via finite differences
  float epsilon = 0.01;
  vec3 neighborX = displace(position + vec3(epsilon, 0.0, 0.0));
  vec3 neighborY = displace(position + vec3(0.0, epsilon, 0.0));
  vec3 tangentX = normalize(neighborX - displaced);
  vec3 tangentY = normalize(neighborY - displaced);
  vNormal = normalize(normalMatrix * normalize(cross(tangentX, tangentY)));

  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
}
