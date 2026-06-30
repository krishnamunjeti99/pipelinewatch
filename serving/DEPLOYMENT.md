# Dashboard Deployment

The PipelineWatch dashboard has two deployment modes.

## 1. Static snapshot (live public demo)
A point-in-time export of the Gold-mart analytics, deployed as a static site
on GitHub Pages. No backend, no credentials — safe to host publicly.
Refresh with `python export_snapshot.py` and redeploy.

**Live:** https://krishnamunjeti99.github.io/pipelinewatch/dashboard/

## 2. Live containerized app
The FastAPI app, containerized via the `Dockerfile`, queries the Gold marts
through Athena in real time. Runs anywhere that runs containers
(ECS/Fargate, Cloud Run, Render, etc.).

```bash
docker build -t pipelinewatch-dashboard .
docker run -p 8000:8000 -e ATHENA_S3_STAGING=... pipelinewatch-dashboard
```

### Credentials in production
Credentials are never baked into the image. In production they are supplied by:
- an **attached IAM role** (e.g. an ECS task role), or
- **short-lived credentials via OIDC role assumption**,

scoped to least privilege — read-only access to Athena, the Glue catalog, and
the Gold S3 prefix only. Long-lived static keys are deliberately avoided.
