FROM astrocrpublic.azurecr.io/runtime:3.2-5

# Isolated virtualenv for dbt — avoids dependency conflicts with Airflow.
RUN python -m venv dbt_venv && \
    . dbt_venv/bin/activate && \
    pip install --no-cache-dir dbt-athena && \
    deactivate
