import {AbsoluteFill} from 'remotion';
import {COLOR, FUENTE, LAYOUT} from '../tema.ts';

// Hoja de papel con una cabecera fina tipo publicación.
export const Fondo: React.FC<{readonly children?: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{background: COLOR.papel, color: COLOR.tinta, fontFamily: FUENTE.sans}}>
    <div
      style={{
        position: 'absolute', left: 60, right: 60, top: 0, height: LAYOUT.mastheadAlto, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', borderBottom: `1px solid ${COLOR.linea}`, fontSize: 18, letterSpacing: 2,
        textTransform: 'uppercase', color: COLOR.gris,
      }}
    >
      <span>Bases de Datos II · TEC</span>
      <span style={{color: COLOR.azul, fontWeight: 600}}>Generador CRUD · PostgreSQL</span>
    </div>
    {children}
  </AbsoluteFill>
);
