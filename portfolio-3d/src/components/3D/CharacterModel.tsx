import React, { useEffect, useMemo, useRef } from 'react';
import { useGLTF, useAnimations, Center } from '@react-three/drei';
import { Group, LoopRepeat } from 'three';
import { useFrame } from '@react-three/fiber';
import { gsap } from 'gsap';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';

const SECTION_ANIMATION_HINTS: Record<string, string[]> = {
  hero: ['wave'],
  about: ['greet', 'hello', 'wave', 'intro', 'idle'],
  projects: ['walk', 'run', 'turn', 'pose', 'idle'],
  experience: ['talk', 'clap', 'celebrate', 'dance', 'idle'],
  tech: ['turn', 'pose', 'stand', 'idle'],
  contact: ['wave', 'greet', 'hello', 'bye', 'idle'],
};

const normalizeName = (value: string) => value.toLowerCase().replace(/[\s_-]+/g, '');

const findBestAnimation = (
  actionNames: string[],
  section: keyof typeof SECTION_ANIMATION_HINTS
) => {
  const normalizedNames = actionNames.map((name) => ({
    original: name,
    normalized: normalizeName(name),
  }));

  for (const hint of SECTION_ANIMATION_HINTS[section]) {
    const normalizedHint = normalizeName(hint);
    const exactMatch = normalizedNames.find((entry) => entry.normalized === normalizedHint);
    if (exactMatch) return exactMatch.original;

    const partialMatch = normalizedNames.find((entry) =>
      entry.normalized.includes(normalizedHint)
    );
    if (partialMatch) return partialMatch.original;
  }

  return actionNames[0];
};

interface CharacterModelProps {
  modelUrl: string;
}

export const CharacterModel: React.FC<CharacterModelProps> = ({ modelUrl }) => {
  const modelRef = useRef<Group>(null);
  const currentActionRef = useRef<string | null>(null);
  const floatOffsetRef = useRef(0);
  const { scene, animations } = useGLTF(modelUrl);
  const clonedScene = useMemo(() => clone(scene), [scene]);
  const { actions } = useAnimations(animations, modelRef);

  const sectionSteps: Array<{
    at: number;
    animation: keyof typeof SECTION_ANIMATION_HINTS;
    position: { x: number; y: number; z: number };
    rotationY: number;
    scale: number;
    transitionRotationY: number;
    settleRotationY: number;
  }> = [
      {
        at: 0,
        animation: 'about',
        position: { x: -1.35, y: -0.85, z: 0.9 },
        rotationY: 0.45,
        scale: 2.15,
        transitionRotationY: 0.22,
        settleRotationY: 0.45,
      },
      {
        at: 1,
        animation: 'projects',
        position: { x: 1.45, y: -0.55, z: -0.8 },
        rotationY: -0.15,
        scale: 2.05,
        transitionRotationY: 0.08,
        settleRotationY: -0.15,
      },
      {
        at: 2,
        animation: 'experience',
        position: { x: 2.1, y: -0.05, z: 0.45 },
        rotationY: -0.38,
        scale: 1.95,
        transitionRotationY: -0.22,
        settleRotationY: -0.38,
      },
      {
        at: 3,
        animation: 'tech',
        position: { x: 1.2, y: -0.35, z: 0.6 },
        rotationY: -0.08,
        scale: 2,
        transitionRotationY: -0.28,
        settleRotationY: -0.08,
      },
      {
        at: 4,
        animation: 'contact',
        position: { x: -1.85, y: -0.75, z: 1.4 },
        rotationY: 0.25,
        scale: 2,
        transitionRotationY: 0.05,
        settleRotationY: 0.25,
      },
    ];

  useEffect(() => {
    const actionNames = actions ? Object.keys(actions) : [];
    if (actionNames.length > 0) {
      console.log('Available model animations:', actionNames);
    } else {
      console.log('No embedded animation clips found for model:', modelUrl);
    }

    const playAnimation = (section: keyof typeof SECTION_ANIMATION_HINTS) => {
      if (!actions || actionNames.length === 0) return;

      const nextActionName = findBestAnimation(actionNames, section);
      const nextAction = actions[nextActionName];
      const currentActionName = currentActionRef.current;

      if (!nextAction || currentActionName === nextActionName) return;

      const previousAction = currentActionName ? actions[currentActionName] : undefined;

      nextAction.reset();
      nextAction.enabled = true;
      nextAction.setLoop(LoopRepeat, Infinity);
      nextAction.timeScale = section === 'projects' ? 1.08 : 1;
      nextAction.fadeIn(0.45);
      nextAction.play();

      if (previousAction) {
        previousAction.fadeOut(0.45);
      }

      currentActionRef.current = nextActionName;
    };

    playAnimation('hero');

    if (!modelRef.current) return;

    modelRef.current.position.set(2.08, -1.2, 0.68);
    modelRef.current.rotation.set(0, 0.02, 0);
    modelRef.current.scale.setScalar(2.5);

    const timeline = gsap.timeline({
      scrollTrigger: {
        trigger: '#main-scroll-container',
        start: 'top top',
        endTrigger: '#contact',
        end: 'bottom bottom',
        scrub: 1,
      },
    });

    sectionSteps.forEach((step) => {
      timeline.call(() => playAnimation(step.animation), [], Math.max(step.at - 0.12, 0));

      timeline
        .to(
          modelRef.current!.position,
          {
            ...step.position,
            onReverseComplete: () => {
              if (step.at === 0) playAnimation('hero');
            },
            duration: 0.9,
            ease: 'power2.inOut',
          },
          step.at
        )
        .to(
          modelRef.current!.rotation,
          {
            y: step.transitionRotationY,
            duration: 0.38,
            ease: 'power2.out',
          },
          step.at
        )
        .to(
          modelRef.current!.rotation,
          {
            y: step.settleRotationY,
            duration: 0.52,
            ease: 'power2.inOut',
          },
          step.at + 0.38
        )
        .to(
          modelRef.current!.scale,
          {
            x: step.scale * 1.04,
            y: step.scale * 1.04,
            z: step.scale * 1.04,
            duration: 0.34,
            ease: 'power2.out',
          },
          step.at
        )
        .to(
          modelRef.current!.scale,
          {
            x: step.scale,
            y: step.scale,
            z: step.scale,
            duration: 0.56,
            ease: 'power2.inOut',
          },
          step.at + 0.34
        );
    });

    return () => {
      timeline.kill();
      actionNames.forEach((name) => actions?.[name]?.stop());
      currentActionRef.current = null;
    };
  }, [actions, modelUrl]);

  useFrame((state) => {
    if (!modelRef.current) return;

    const nextOffset = Math.sin(state.clock.elapsedTime * 2) * 0.04;
    modelRef.current.position.y += nextOffset - floatOffsetRef.current;
    floatOffsetRef.current = nextOffset;
  });

  useEffect(() => {
    return () => {
      floatOffsetRef.current = 0;
    };
  }, []);

  return (
    <group ref={modelRef} dispose={null}>
      <Center>
        <primitive object={clonedScene} />
      </Center>
    </group>
  );
};

useGLTF.preload('/model.glb');
