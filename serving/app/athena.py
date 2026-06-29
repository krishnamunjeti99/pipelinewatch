"""
Athena query layer for the PipelineWatch dashboard.

Connects to Athena and runs read-only queries against the Gold marts.
Kept separate from the web layer so it can be tested independently.
"""
import os

import pandas as pd
from pyathena import connect
from pyathena.pandas.cursor import PandasCursor

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
S3_STAGING = os.environ["ATHENA_S3_STAGING"]
DATABASE = os.environ.get("GLUE_DATABASE", "pipelinewatch_gold")


def _cursor():
    """Create a pandas-returning Athena cursor."""
    return connect(
        s3_staging_dir=S3_STAGING,
        region_name=AWS_REGION,
        schema_name=DATABASE,
        cursor_class=PandasCursor,
    ).cursor()


def query(sql: str) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    return _cursor().execute(sql).as_pandas()
