# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Filter the data for spam placements and exclude them in Google Ads."""
import base64
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Union
import uuid
import google.auth
import google.auth.credentials
from googleapiclient.discovery import build
from google.ads.googleads.client import GoogleAdsClient
from google.cloud import bigquery
import jsonschema
import pandas as pd
from utils import gcs


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The Google Cloud project
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
# The bucket to write the data to
APE_GCS_DATA_BUCKET = os.environ.get('APE_GCS_DATA_BUCKET')
# The name of the BigQuery Dataset
BQ_DATASET = os.environ.get('APE_BIGQUERY_DATASET')
# Set False to apply the exclusions in Google Ads. If True, the call will be
# made to the API and validated, but the exclusion won't be applied and you
# won't see it in the UI. You probably want this to be True in a dev environment
# and False in prod.
VALIDATE_ONLY = os.environ.get(
    'APE_EXCLUSION_VALIDATE_ONLY', 'False').lower() in ('true', '1', 't')

# The access scopes used in this function
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/cloud-platform',
]

# The schema of the JSON in the event payload
message_schema = {
    'type': 'object',
    'properties': {
        'sheet_id': {'type': 'string'},
        'customer_id': {'type': 'string'},
    },
    'required': ['sheet_id', 'customer_id', ]
}


def main(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """The entry point: extract the data from the payload and starts the job.

    The pub/sub message must match the message_schema object above.

    Args:
        event: A dictionary representing the event data payload.
        context: An object containing metadata about the event.

    Raises:
        jsonschema.exceptions.ValidationError if the message from pub/sub is not
        what is expected.
    """
    del context
    logger.info('Google Ads Exclusion service triggered.')
    logger.info('Message: %s', event)
    message = base64.b64decode(event['data']).decode('utf-8')
    logger.info('Decoded message: %s', message)
    message_json = json.loads(message)
    logger.info('JSON message: %s', message_json)

    # Will raise jsonschema.exceptions.ValidationError if the schema is invalid
    jsonschema.validate(instance=message_json, schema=message_schema)

    run(message_json.get('customer_id'), message_json.get('sheet_id'))

    logger.info('Done')


def run(customer_id: str, sheet_id: str) -> None:
    """Start the job to run the report from Google Ads & output it.

    Args:
        customer_id: the Google Ads customer ID to process.
        sheet_id: the ID of the Google Sheet containing the config.
    """
    logger.info('Starting job to fetch data for %s', customer_id)
    credentials = get_auth_credentials()
    filters = get_config_filters(sheet_id, credentials)

    placements = get_spam_placements(customer_id, filters, credentials)
    if placements is not None:
        exclude_placements_in_gads(placements, sheet_id, credentials)
        write_results_to_gcs(customer_id, placements)
    logger.info('Job complete')


def get_auth_credentials() -> google.auth.credentials.Credentials:
    """Return credentials for Google APIs."""
    credentials, project_id = google.auth.default(scopes=SCOPES)
    return credentials


def get_config_filters(sheet_id: str,
                       credentials: google.auth.credentials.Credentials) -> str:
    """Get the filters for identifying a spam placement from the config.

    Args:
        sheet_id: the ID of the Google Sheet containing the config.
        credentials: Google Auth credentials

    Returns:
        SQL WHERE conditions for that can be run on BigQuery, e.g.
        view_count > 1000000 AND subscriber_count > 10000
    """
    logger.info('Getting config from sheet %s', sheet_id)

    result = get_range_values_from_sheet(
        sheet_id, 'yt_exclusion_filters', credentials)

    logger.info('Returned %i rows', len(result))
    filters = youtube_filters_to_sql_string(result)
    if len(filters) == 0:
        raise google.api_core.exceptions.BadRequest("Filters are not set")

    return filters


def get_range_values_from_sheet(
        sheet_id: str,
        sheet_range: str,
        credentials: google.auth.credentials.Credentials
) -> List[List[str]]:
    """Get the values from a named range in the Google Sheet.

    Args:
        sheet_id: the Google Sheet ID to fetch data from.
        sheet_range: the range in the Google Sheet to get the values from
        credentials: Google Auth credentials

    Returns:
        Each row in the response represents a row in the Sheet.
    """
    logger.info(f'Getting range "{sheet_range}" from sheet: {sheet_id}')
    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet = sheets_service.spreadsheets()
    return sheet.values().get(
        spreadsheetId=sheet_id,
        range=sheet_range).execute().get('values', [])


def youtube_filters_to_sql_string(config_filters: List[List[str]]) -> str:
    """Turn the YouTube  filters into a SQL compatible string.

    The config sheet has the filters in a list of lists, these need to be
    combined, so they can be used in a WHERE clause in the SQL.

    Each row is "AND" together.

    Args:
        config_filters: the filters from the Google Sheet

    Returns:
        A string that can be used in the WHERE statement of SQL Language.
    """
    conditions = []
    for row in config_filters:
        if len(row) == 3:
            conditions.append(f'{row[0]} {row[1]} {row[2]}')

    return ' AND '.join(conditions)


def get_spam_placements(customer_id: str,
                        filters: str,
                        credentials: google.auth.credentials.Credentials
                        ) -> Union[List[str], None]:
    """Run a query to find spam placements in BigQuery and return as a list.

    Args:
        customer_id: the Google Ads customer ID to process.
        filters: a string containing WHERE conditions to add to the query based
            on the config Google Sheet.
        credentials: Google Auth credentials

    Returns:
        A list of placement IDs which should be excluded.
    """

    logger.info('Getting spam placements from BigQuery')
    logger.info('Connecting to: %s BigQuery', GOOGLE_CLOUD_PROJECT)
    client = bigquery.Client(
        project=GOOGLE_CLOUD_PROJECT, credentials=credentials)

    query = f"""
        SELECT DISTINCT
            Yt.channel_id
        FROM
            `{BQ_DATASET}.google_ads_report` AS Ads
        LEFT JOIN
            {BQ_DATASET}.youtube_channel AS Yt
            USING(channel_id)
        LEFT JOIN
            `{BQ_DATASET}.google_ads_exclusion` AS Excluded
            USING(channel_id)
        WHERE
            Ads.customer_id = "{customer_id}"
            AND Excluded.channel_id IS NULL
            AND (
                Excluded.customer_id = "{customer_id}"
                OR Excluded.customer_id IS NULL
            )
            AND {filters}
        """
    logger.info('Running query: %s', query)

    rows = client.query(query).result()

    if rows.total_rows == 0:
        logger.info('There is nothing to update')
        return None
    channel_ids = []
    for row in rows:
        channel_ids.append(row.channel_id)
    logger.info('Received %s channel_ids', len(channel_ids))
    return channel_ids


def exclude_placements_in_gads(
        placements: List[str],
        sheet_id: str,
        credentials: google.auth.credentials.Credentials = None
) -> None:
    """Exclude the placements in the Google Ads account.

    Args:
        placements: a list of YouTube channel IDs which should be excluded.
        sheet_id: the ID of the Google Sheet containing the config.
        credentials: Google Auth credentials
    """
    logger.info('Excluding placements in Google Ads.')

    if credentials is None:
        logger.info('No auth credentials provided. Fetching them.')
        credentials = get_auth_credentials()

    shared_set_id = get_range_values_from_sheet(
        sheet_id=sheet_id,
        sheet_range='placement_exclusion_list_id',
        credentials=credentials)[0][0]
    customer_id = get_range_values_from_sheet(
        sheet_id=sheet_id,
        sheet_range='placement_exclusion_customer_id',
        credentials=credentials)[0][0]

    client = GoogleAdsClient.load_from_env(version='v11')
    service = client.get_service('SharedCriterionService')

    shared_set = f'customers/{customer_id}/sharedSets/{shared_set_id}'

    operations = []
    logger.info('Processing the %i placements', len(placements))
    for placement in placements:
        operation = client.get_type('SharedCriterionOperation')
        criterion = operation.create
        criterion.shared_set = shared_set
        criterion.youtube_channel.channel_id = placement
        operations.append(operation)

    placements_len = len(placements)
    logger.info('There are %i operations to upload', placements_len)
    logger.info('Validate_only mode: %s', VALIDATE_ONLY)
    if placements_len > 0:
        response = service.mutate_shared_criteria(
            request={
                'validate_only': VALIDATE_ONLY,
                'customer_id': customer_id,
                'operations': operations
            }
        )
        logger.info('Response from the upload:')
        logger.info(response)

    logger.info('Done.')


def write_results_to_gcs(customer_id: str,
                         placements: List[str],
                         ) -> None:
    """Write the exclusions to GCS as a CSV file.

    Historical data is preserved so all file writes have a UUID appended to it.

     Args:
        customer_id: the Google Ads customer ID to process.
        placements: alist of placement IDs which should be excluded.
    """
    exclusions_df = pd.DataFrame(placements, columns=[
        'channel_id',
    ])
    exclusions_df['customer_id'] = int(customer_id)
    exclusions_df['datetime_updated'] = datetime.now()

    logger.info('Writing results to GCS: %s', APE_GCS_DATA_BUCKET)
    number_of_rows = len(exclusions_df.index)
    logger.info('There are %s rows', number_of_rows)
    if number_of_rows > 0:
        uuid_str = str(uuid.uuid4())
        blob_name = f'google_ads_exclusion/{customer_id}-{uuid_str}.csv'
        logger.info('Blob name: %s', blob_name)
        gcs.upload_blob_from_df(
            df=exclusions_df,
            blob_name=blob_name,
            bucket=APE_GCS_DATA_BUCKET)
        logger.info('Blob uploaded to GCS')
    else:
        logger.info('There is nothing to write to GCS')
