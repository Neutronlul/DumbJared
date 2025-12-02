FROM node:24-bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    adduser pwuser

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN mkdir /ms-playwright && \
    npx -y playwright@1.56.0 install --with-deps --only-shell chromium && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.npm && \
    chmod -R 777 /ms-playwright