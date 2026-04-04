'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { ribbonVertexShader, ribbonFragmentShader } from './shaders';

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
        vertexShader={ribbonVertexShader}
        fragmentShader={ribbonFragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}
