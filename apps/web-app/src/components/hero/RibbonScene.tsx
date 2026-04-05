'use client';

import { Canvas } from '@react-three/fiber';
import { useRef, useSyncExternalStore } from 'react';
import * as THREE from 'three';
import { RibbonMesh } from './RibbonMesh';

function subscribeMobile(cb: () => void) {
  window.addEventListener('resize', cb);
  return () => window.removeEventListener('resize', cb);
}
function getMobile() { return window.innerWidth < 768; }
function getMobileServer() { return false; }



interface RibbonSceneProps {
  onReady?: () => void;
}

export function RibbonScene({ onReady }: RibbonSceneProps) {
  const mouseRef = useRef(new THREE.Vector2(0, 0));
  const mobile = useSyncExternalStore(subscribeMobile, getMobile, getMobileServer);

  return (
    <Canvas
      gl={{
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
        outputColorSpace: THREE.SRGBColorSpace,
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.2,
      }}
      camera={{ fov: 50, position: [0, 0, 8] }}
      dpr={mobile ? [1, 1] : [1, 1.5]}
      frameloop="always"
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      onCreated={() => onReady?.()}
    >
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1.0} />
      <RibbonMesh mouseRef={mouseRef} mobile={mobile} />
    </Canvas>
  );
}
