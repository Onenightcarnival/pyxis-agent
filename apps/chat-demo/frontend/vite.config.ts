import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 把后端 SSE 端点代理到 3001，前端同源无 CORS 烦恼
    proxy: {
      "/api": {
        target: "http://localhost:3001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
        // 流式响应：把 content-length 去掉，让浏览器按 chunked 逐块收流，
        // 不要等整个响应攒完再 flush。
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            delete proxyRes.headers["content-length"];
          });
        },
      },
    },
  },
});
