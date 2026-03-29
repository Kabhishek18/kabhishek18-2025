import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Sparkles, Environment } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { CharacterModel } from './CharacterModel';

interface HeroCanvasProps {
  modelUrl: string;
}

export const HeroCanvas: React.FC<HeroCanvasProps> = ({ modelUrl }) => {
  return (
    <Canvas 
      camera={{ position: [0, 0, 5], fov: 45 }} 
      gl={{ alpha: true, antialias: true }}
      dpr={[1, 2]}
    >
      <Suspense fallback={null}>
        {/* Cinematic Lighting Setup */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 10, 5]} intensity={1} color="#ffffff" />
        <pointLight position={[-5, 0, -5]} intensity={5} color="#00f0ff" />
        <pointLight position={[5, -5, 5]} intensity={3} color="#ff6b98" />

        {/* Character Object */}
        <CharacterModel modelUrl={modelUrl} />

        {/* Ambient environment floating particles */}
        <Sparkles 
          count={150} 
          scale={10} 
          size={2} 
          speed={0.4} 
          opacity={0.3} 
          color="#8ff5ff" 
        />

        {/* Studio environment for realistic PBR reflections */}
        <Environment preset="city" />

        {/* Post-Processing (Bloom) for cinematic neon glow */}
        <EffectComposer>
          <Bloom 
            luminanceThreshold={0.5} 
            mipmapBlur 
            intensity={1.5} 
          />
        </EffectComposer>
        
        {/* Subtle camera control (optional) */}
        <OrbitControls 
          enableZoom={false} 
          enablePan={false}
          maxPolarAngle={Math.PI / 2 + 0.1}
          minPolarAngle={Math.PI / 2 - 0.1}
        />
      </Suspense>
    </Canvas>
  );
};
