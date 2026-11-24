"use client";

import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

interface SkyDomeProps {
  horizonColor: string;
  topColor: string;
}

const SKY_VERTEX_SHADER = /* glsl */ `
  varying vec3 vWorldDir;
  void main() {
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vWorldDir = position;
    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

const SKY_FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 uHorizon;
  uniform vec3 uTop;
  varying vec3 vWorldDir;
  void main() {
    float h = clamp(normalize(vWorldDir).y * 1.45, 0.0, 1.0);
    vec3 col = mix(uHorizon, uTop, pow(h, 0.62));
    gl_FragColor = vec4(col, 1.0);
    #include <colorspace_fragment>
  }
`;

export default function SkyDome({ horizonColor, topColor }: SkyDomeProps) {
  const matRef = useRef<THREE.ShaderMaterial | null>(null);

  const uniforms = useMemo(
    () => ({
      uHorizon: { value: new THREE.Color("#CDE4F9") },
      uTop: { value: new THREE.Color("#6DA8E3") },
    }),
    [],
  );

  useEffect(() => {
    if (!matRef.current) {
      return;
    }
    matRef.current.uniforms.uHorizon.value.set(horizonColor);
    matRef.current.uniforms.uTop.value.set(topColor);
  }, [horizonColor, topColor]);

  return (
    <mesh renderOrder={-10} frustumCulled={false}>
      <sphereGeometry args={[2900, 24, 16]} />
      <shaderMaterial
        ref={matRef}
        uniforms={uniforms}
        vertexShader={SKY_VERTEX_SHADER}
        fragmentShader={SKY_FRAGMENT_SHADER}
        side={THREE.BackSide}
        depthWrite={false}
        fog={false}
      />
    </mesh>
  );
}
