FROM golang:1.24-alpine AS build
RUN apk add --no-cache git
WORKDIR /src
# Community Edition distribuida como fonte; objeto da tag fixo do release 2025-04-22.
RUN git init && git remote add origin https://github.com/minio/minio.git \
    && git fetch --depth 1 origin f19c534b9f457773dcd043d977433e1a71525c3b \
    && git checkout --detach FETCH_HEAD
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM alpine:3.21
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
      org.opencontainers.image.revision="0d7408fc9969caf07de6a8c3a84f9fbb10a6739e" \
      org.opencontainers.image.licenses="AGPL-3.0-only"
RUN apk add --no-cache ca-certificates && adduser -D -u 10001 minio && mkdir /data && chown minio /data
COPY --from=build /out/minio /usr/local/bin/minio
COPY --from=build /src/LICENSE /usr/share/licenses/minio/LICENSE
USER minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
