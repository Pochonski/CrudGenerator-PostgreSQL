import {AbsoluteFill} from 'remotion';

export const Fondo: React.FC<{readonly children?: React.ReactNode}> = ({children}) => (
  <AbsoluteFill
    style={{
      background:
        'radial-gradient(1200px 700px at 15% 0%, #162350 0%, transparent 60%), radial-gradient(900px 600px at 100% 100%, #141c3c 0%, transparent 60%), #0b1020',
      color: '#e6ebf5',
      fontFamily: '"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif',
    }}
  >
    {children}
  </AbsoluteFill>
);
