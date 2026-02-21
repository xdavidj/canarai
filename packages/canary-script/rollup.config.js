import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

export default {
  input: 'src/index.ts',
  output: {
    file: 'dist/canary.js',
    format: 'iife',
    name: 'Canary',
    sourcemap: false,
  },
  plugins: [
    resolve(),
    typescript({
      tsconfig: './tsconfig.json',
    }),
    terser({
      compress: {
        drop_console: true,
        passes: 2,
      },
      mangle: {
        reserved: ['Canary'],
      },
      format: {
        comments: false,
      },
    }),
  ],
};
