# Streamlit Deployment

## Deployment Mode

The public deployment should run in deterministic mode by default.

Recommended environment variables:

```text
LLM_ENABLED=false
LLM_PROVIDER=volcengine
ARK_API_KEY=
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
ARK_MODEL=your_model_or_endpoint_id_here
```

## Deployment Steps

1. Push the repository to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app from this repository.
4. Set the main file path to `src/app.py`.
5. Configure environment variables with `LLM_ENABLED=false`.
6. Deploy the app.
7. Replace the placeholder README badge with the deployed app URL.

## Notes

- Do not store API keys in the repository.
- For public demos, deterministic mode is recommended.
- LLM-enhanced mode can be enabled in private deployments with secrets
  configured in the platform.

