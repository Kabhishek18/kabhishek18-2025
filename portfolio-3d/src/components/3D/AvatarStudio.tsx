import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../Button';
import './AvatarStudio.css';

type ExportPayload = Record<string, unknown>;

interface AvatarStudioProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (payload: ExportPayload, glbUrl: string) => void;
}

interface AvaturnSdkInstance {
  init: (container: HTMLElement, options: { url: string }) => Promise<void>;
  on: (eventName: 'export', callback: (payload: ExportPayload) => void) => void;
}

interface AvaturnSdkConstructor {
  new (): AvaturnSdkInstance;
}

const SDK_URL = 'https://cdn.jsdelivr.net/npm/@avaturn/sdk/dist/index.js';
const AVATURN_SUBDOMAIN = import.meta.env.VITE_AVATURN_SUBDOMAIN ?? 'demo';

const findGlbUrl = (value: unknown): string | null => {
  if (!value) return null;

  if (typeof value === 'string') {
    const normalized = value.toLowerCase();
    if (normalized.endsWith('.glb') || normalized.includes('.glb?')) {
      return value;
    }
    return null;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const result = findGlbUrl(item);
      if (result) return result;
    }
    return null;
  }

  if (typeof value === 'object') {
    for (const nestedValue of Object.values(value)) {
      const result = findGlbUrl(nestedValue);
      if (result) return result;
    }
  }

  return null;
};

let sdkPromise: Promise<AvaturnSdkConstructor> | null = null;

const loadSdk = async () => {
  if (!sdkPromise) {
    sdkPromise = import(/* @vite-ignore */ SDK_URL).then(
      (module) => (module as { AvaturnSDK: AvaturnSdkConstructor }).AvaturnSDK
    );
  }

  return sdkPromise;
};

export const AvatarStudio: React.FC<AvatarStudioProps> = ({
  isOpen,
  onClose,
  onExport,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sdkRef = useRef<AvaturnSdkInstance | null>(null);
  const exportBoundRef = useRef(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    let cancelled = false;

    const setup = async () => {
      try {
        setStatus('loading');
        setErrorMessage('');

        const AvaturnSDK = await loadSdk();
        if (cancelled || !containerRef.current) return;

        const sdk = new AvaturnSDK();
        sdkRef.current = sdk;

        await sdk.init(containerRef.current, {
          url: `https://${AVATURN_SUBDOMAIN}.avaturn.dev`,
        });

        if (cancelled) return;

        if (!exportBoundRef.current) {
          sdk.on('export', (payload) => {
            const glbUrl = findGlbUrl(payload);
            if (!glbUrl) {
              setStatus('error');
              setErrorMessage('Avatar export completed, but no GLB URL was found in the response.');
              console.log('Avaturn export payload:', payload);
              return;
            }

            console.log('Avaturn export payload:', payload);
            onExport(payload, glbUrl);
            onClose();
          });
          exportBoundRef.current = true;
        }

        setStatus('ready');
      } catch (error) {
        console.error('Failed to load Avaturn SDK', error);
        setStatus('error');
        setErrorMessage(
          'Avaturn could not be loaded. Check your subdomain or network access and try again.'
        );
      }
    };

    setup();

    return () => {
      cancelled = true;
      sdkRef.current = null;
      exportBoundRef.current = false;

      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [isOpen, onClose, onExport]);

  if (!isOpen) return null;

  return (
    <div className="avatar-studio-overlay" role="dialog" aria-modal="true" aria-label="Avatar Studio">
      <div className="avatar-studio-shell glass-panel">
        <div className="avatar-studio-header">
          <div>
            <p className="label-md">Avatar Studio</p>
            <h2 className="title-lg">Build your Avaturn character</h2>
          </div>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>

        <p className="body-lg avatar-studio-copy">
          Export your avatar in Avaturn and this portfolio will swap the current GLB for the exported model automatically.
        </p>

        {status === 'error' && <p className="avatar-studio-error">{errorMessage}</p>}

        <div className="avatar-studio-frame">
          {status === 'loading' && (
            <div className="avatar-studio-loading">
              <p className="label-md">Loading Avaturn...</p>
            </div>
          )}
          <div
            id="avaturn-sdk-container"
            ref={containerRef}
            className={`avatar-studio-container ${status === 'loading' ? 'is-hidden' : ''}`}
          />
        </div>
      </div>
    </div>
  );
};
