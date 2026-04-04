'use client';

import { useSyncExternalStore } from 'react';

function getWebGLSupport() {
  if (typeof window === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    return !!gl;
  } catch {
    return false;
  }
}

const cached = { value: false, checked: false };

function subscribe() {
  return () => {};
}

function getSnapshot() {
  if (!cached.checked) {
    cached.value = getWebGLSupport();
    cached.checked = true;
  }
  return cached.value;
}

function getServerSnapshot() {
  return false;
}

export function useWebGLSupport(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
