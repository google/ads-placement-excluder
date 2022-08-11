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
from typing import Any, Dict, List
from google.ads.googleads.client import GoogleAdsClient
import google.auth
import google.auth.credentials
from googleapiclient.discovery import build
from google.cloud import bigquery
import jsonschema


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The Google Cloud project containing the BigQuery dataset
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
# The ID of the Google Sheet containing the config
SHEET_ID = os.environ.get('APE_CONFIG_SHEET_ID')

# The access scopes used in this function
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
# The range in the sheet containing the config data
SHEET_RANGE = 'Google Ads!A2:D'


# The schema of the JSON in the event payload
message_schema = {
    'type': 'object',
    'properties': {
        'customer_id': {'type': 'string'},
    },
    'required': ['customer_id', ]
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

    run(message_json.get('customer_id'))

    logger.info('Done')


def run(customer_id: str) -> None:
    """Start the job to run the report from Google Ads & output it.

    Args:
        customer_id: the Google Ads customer ID to process.
    """
    logger.info('Starting job to fetch data for %s', customer_id)
    credentials = get_auth_credentials()
    filters = get_config_filters(customer_id, credentials)
    placements = get_spam_placements(customer_id, filters, credentials)
    exclude_placements_in_gads(customer_id, placements)
    write_exclusions_to_bigquery(customer_id, placements, credentials)
    logger.info('Job complete')


def get_auth_credentials() -> google.auth.credentials.Credentials:
    """Return credentials for Google APIs."""
    credentials, project_id = google.auth.default(scopes=SCOPES)
    return credentials


def get_config_filters(customer_id: str,
                       credentials: google.auth.credentials.Credentials) -> str:
    """Get the filters for identifying a spam placement from the config.

    Args:
        customer_id: the Google Ads customer ID to process.
        credentials: Google Auth credentials

    Returns:
        SQL WHERE conditions for that can be run on BigQuery, e.g.
        viewCount > 1000000 AND subscriberCount > 100000
    """
    logger.info('Getting config from sheet %s for %s', (SHEET_ID, customer_id))

    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SHEET_ID,
                                range=SHEET_RANGE).execute()
    rows = result.get('values', [])
    logger.info('Returned %i rows', len(rows))

    where_str = ''

    for row in rows:
        if row[0] == customer_id:
            print(row)
            break
        # Do something useful

    return where_str


def get_spam_placements(customer_id: str,
                        filters: str,
                        credentials: google.auth.credentials.Credentials
) -> List[str]:
    """Run a query to find spam placements in BigQuery and return as a list.

    Args:
        customer_id: the Google Ads customer ID to process.
        filters: a string containing WHERE conditions to add to the query based
            on the config Google Sheet.

    Returns:
        A list of placement IDs which should be excluded.
    """
    logger.info('Getting spam placements from BigQuery')
    client = bigquery.Client(project=GOOGLE_CLOUD_PROJECT,
                             credentials=credentials)
    # do something
    return ['abc-123']


def exclude_placements_in_gads(customer_id: str, placements: List[str]) -> None:
    """Exclude the placements in the Google Ads account.

    Args:
        customer_id: the Google Ads customer ID to process.
        placements: alist of placement IDs which should be excluded.
    """
    logger.info('Excluding placements in Google Ads.')
    client = GoogleAdsClient.load_from_env(version='v11')
    ga_service = client.get_service("GoogleAdsService")

    # Exclude placements

    logger.info('Done.')


def write_exclusions_to_bigquery(customer_id: str,
                                 placements: List[str],
                                 credentials: google.auth.credentials.Credentials
) -> None:
    """Write the exclusions to BigQuery to maintain history of changes.

     Args:
        customer_id: the Google Ads customer ID to process.
        placements: alist of placement IDs which should be excluded.
        credentials: Google Auth credentials

    Returns:
        A list of placement IDs which should be excluded.
    """
    logger.info('Writing exclusions to BigQuery')
    client = bigquery.Client(project=GOOGLE_CLOUD_PROJECT,
                             credentials=credentials)

    # Append exclusions to BigQuery - we want to maintain a history of these
    # changes
