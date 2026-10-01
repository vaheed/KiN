# KIN pins the published TrueForge application version while following the
# upstream production Dockerfile shape: Node runtime + npm package install.
FROM node:24-slim

WORKDIR /app

ENV NODE_ENV=production \
    STANDALONE=false \
    HOST=0.0.0.0 \
    PORT=8790

ARG TRUEFORGE_VERSION=0.3.1

RUN npm install --omit=dev "@truefoundry/trueforge@${TRUEFORGE_VERSION}" \
    && npm cache clean --force

EXPOSE 8790

CMD ["node", "node_modules/@truefoundry/trueforge/dist/main.js"]
