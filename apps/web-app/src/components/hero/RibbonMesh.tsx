'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const vertexShader = /* glsl */ `
precision mediump float;

uniform float uTime;
uniform vec2 uMouse;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vPosition;
varying float vElevation;

void main() {
  vUv = uv;
  vec3 pos = position;

  // Multi-frequency wave deformation for organic flow
  float wave1 = sin(pos.x * 0.5 + uTime * 0.3) * 1.5;
  float wave2 = cos(pos.x * 0.3 + pos.y * 0.2 + uTime * 0.2) * 1.0;
  float wave3 = sin(pos.x * 0.8 - uTime * 0.15) * 0.5;
  float wave4 = cos(pos.y * 0.4 + uTime * 0.25) * 0.8;

  pos.z += wave1 + wave2 + wave3 + wave4;

  // Twist along X axis
  float twist = sin(pos.x * 0.2 + uTime * 0.1) * 0.5;
  float cosT = cos(twist);
  float sinT = sin(twist);
  float newY = pos.y * cosT - pos.z * sinT;
  float newZ = pos.y * sinT + pos.z * cosT;
  pos.y = newY;
  pos.z = newZ;

  // Subtle mouse influence
  pos.x += uMouse.x * 0.3;
  pos.y += uMouse.y * 0.2;

  vElevation = pos.z;
  vPosition = (modelMatrix * vec4(pos, 1.0)).xyz;

  // Approximate normal via finite differences
  vec3 posA = pos;
  posA.x += 0.01;
  vec3 posB = pos;
  posB.y += 0.01;
  vNormal = normalize(cross(posA - pos, posB - pos));

  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
`;

const fragmentShader = /* glsl */ `
precision mediump float;

uniform float uTime;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorC;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vPosition;
varying float vElevation;

void main() {
  // Gradient with slow iridescence shift
  float gradientT = vUv.x + sin(uTime * 0.1) * 0.2;
  vec3 color = mix(uColorA, uColorB, smoothstep(0.0, 0.5, gradientT));
  color = mix(color, uColorC, smoothstep(0.5, 1.0, gradientT));

  // Elevation-based brightness (folds catch light)
  float brightness = 0.7 + vElevation * 0.1;
  color *= brightness;

  // Fresnel edge glow
  vec3 viewDir = normalize(cameraPosition - vPosition);
  float fresnel = pow(1.0 - max(dot(normalize(vNormal), viewDir), 0.0), 3.0);
  color += fresnel * 0.3;

  // Fiber texture
  float fiber = sin(vUv.y * 200.0 + vUv.x * 50.0) * 0.03;
  color += fiber;

  // Edge transparency
  float alpha = smoothstep(0.0, 0.05, vUv.y) * smoothstep(1.0, 0.95, vUv.y);
  alpha *= 0.85 + fresnel * 0.15;

  gl_FragColor = vec4(color, alpha);
}
`;

interface RibbonMeshProps {
  mouseRef: React.RefObject<THREE.Vector2>;
  mobile?: boolean;
}

export function RibbonMesh({ mouseRef, mobile = false }: RibbonMeshProps) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uColorA: { value: new THREE.Color('#2563eb') },
      uColorB: { value: new THREE.Color('#06b6d4') },
      uColorC: { value: new THREE.Color('#8b5cf6') },
    }),
    [],
  );

  const segments: [number, number] = mobile ? [100, 30] : [200, 60];

  useFrame((_state, delta) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime!.value += delta;
    const u = materialRef.current.uniforms.uMouse!.value as THREE.Vector2;
    u.lerp(mouseRef.current, 0.05);
  });

  return (
    <mesh rotation={[0.15, 0, 0]}>
      <planeGeometry args={[20, 6, segments[0], segments[1]]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}
