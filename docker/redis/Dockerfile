FROM redis:7-alpine
EXPOSE 6379

VOLUME /data

CMD ["redis-server", "--appendonly", "yes"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD redis-cli ping | grep -q PONG