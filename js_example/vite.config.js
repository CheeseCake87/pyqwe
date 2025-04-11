import {defineConfig} from 'vite'
import solidPlugin from 'vite-plugin-solid'
import devtools from 'solid-devtools/vite';

export default defineConfig({
    plugins: [
        devtools({
            autoname: true,
        }),
        solidPlugin(),
    ],
    root: 'src',
    server: {
        host: '127.0.0.1',
        port: 5011
    },
    build: {
        target: 'esnext',
        outDir: '../dist',
        emptyOutDir: true,
    },
})
