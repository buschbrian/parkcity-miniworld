import { serveR2 } from "./lib/r2.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/tiles/")) {
      const key = url.pathname.slice("/tiles/".length);
      if (!/^[\w-]+\/\d+\/-?\d+\/-?\d+\.jpg$/.test(key)) {
        return new Response("Bad tile path", { status: 400 });
      }
      return serveR2(env, request, key, "image/jpeg", 86400);
    }
    return env.ASSETS.fetch(request);
  },
};
