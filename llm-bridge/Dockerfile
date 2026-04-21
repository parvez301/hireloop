FROM node:20-alpine

# Claude Code CLI, used to serve /v1/messages requests via the user's
# Claude subscription instead of a paid API key.
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY package.json server.js ./

ENV NODE_ENV=production
ENV LLM_BRIDGE_PORT=8019
ENV LLM_BRIDGE_HOST=0.0.0.0
ENV HOME=/root

# Claude Code stores auth + session state under $HOME/.claude. Mount a volume
# here (bind mount on EC2, named volume locally) so auth survives container
# restarts. The first run requires `docker exec -it <ctr> claude login`.
VOLUME ["/root/.claude"]

EXPOSE 8019

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8019/health >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
