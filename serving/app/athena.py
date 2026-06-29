"""
Athena query layer for the PipelineWatch dashboard.

Loads .env automatically, connects to Athena, and runs read-only
queries against the Gold marts. Kept separate from the web layer.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pyathena import connect
from pyathena.pandas.cursor import PandasCursor

# Load serving/.env regardless of where the process was started from.
load_dotenv(Path(__file__).parent.parent / ".env")

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
S3_STAGING = os.environ["ATHENA_S3_STAGING"]
DATABASE = os.environ.get("GLUE_DATABASE", "pipelinewatch_gold")


def _cursor():
    return connect(
        s3_staging_dir=S3_STAGING,
        region_name=AWS_REGION,
        schema_name=DATABASE,
        cursor_class=PandasCursor,
    ).cursor()


def query(sql: str) -> pd.DataFrame:
    return _cursor().execute(sql).as_pandas()
