
/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // VisionQA Özel Renkleri
                primary: {
                    DEFAULT: '#3b82f6', // blue-500
                    foreground: '#ffffff',
                },
                background: '#0f172a', // slate-900 (Dark Mode Base)
            },
        },
    },
    plugins: [],
}
