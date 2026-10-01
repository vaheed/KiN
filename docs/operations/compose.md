# Compose Operations

## Start

```bash
docker compose up -d
```

## Status

```bash
docker compose ps
docker compose logs --tail=200 kin
docker compose logs --tail=200 trueforge
docker compose logs --tail=200 bifrost
```

## Stop

```bash
docker compose down
```

## Reset disposable development data

```bash
docker compose down -v
docker compose up -d
```

This removes both KIN and TrueForge PostgreSQL data and Redis data.

## Health

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8790/healthz
curl http://127.0.0.1:8080/health
```
