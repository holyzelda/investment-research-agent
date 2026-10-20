FROM mcr.microsoft.com/playwright:v1.48.2-noble

# Keep the JavaScript client and the browsers shipped in the base image on the
# same release. The install is isolated inside this tooling-only image.
WORKDIR /opt/prototype-screenshots
RUN npm install --omit=dev --no-package-lock playwright@1.48.2 \
    && npm cache clean --force

COPY capture.cjs /opt/prototype-screenshots/capture.cjs
WORKDIR /workspace

ENTRYPOINT ["node", "/opt/prototype-screenshots/capture.cjs"]
