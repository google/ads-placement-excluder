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
"""Pull YouTube data for the placements in the Google Ads report."""
import base64
from datetime import datetime
import json
import logging
import math
import os
import sys
from typing import Any, Dict, List, Tuple
import google.auth
import google.auth.credentials
from google.cloud import bigquery
from google.cloud import pubsub_v1
from google.cloud import translate_v2 as translate
from googleapiclient.discovery import build
import jsonschema
import pandas as pd
import numpy as np


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The Google Cloud project containing the BigQuery dataset
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

# The pub/sub topic to send the success message to
APE_ADS_EXCLUDER_PUBSUB_TOPIC = os.environ.get('APE_ADS_EXCLUDER_PUBSUB_TOPIC')
SHEET_ID = os.environ.get('APE_CONFIG_SHEET_ID')
# The access scopes used in this function
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The schema of the JSON in the event payload
message_schema = {
    'type': 'object',
    'properties': {
        'sheet_id': {'type': 'string'},
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
    logger.info('YouTube channel service triggered.')
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
    """Orchestration to pull YouTube data and output it to BigQuery.

    Args:
        customer_id: the Google Ads customer ID to process.
        sheet_id: the ID of the Google Sheet containing the config.
    """
    credentials = get_auth_credentials()
    channel_ids = get_placements_query(customer_id, credentials)
    if len(channel_ids) > 0:
        get_youtube_dataframe(channel_ids, credentials)
    else:
        logger.info('No channel IDs to process')
    send_messages_to_pubsub(customer_id, sheet_id)
    logger.info('Done')


def get_auth_credentials() -> google.auth.credentials.Credentials:
    """Return credentials for Google APIs."""
    credentials, project_id = google.auth.default()
    return credentials


def get_placements_query(
        customer_id: str,
        credentials: google.auth.credentials.Credentials
) -> List[str]:
    """Get the placements from the Google Ads report in BigQuery.

    Args:
        customer_id: the Google Ads customer ID to process.
        credentials: Google Auth credentials

    Returns:
        A list of placement IDs that need to be pulled from YouTube
    """
    logger.info('Getting Placements from Google Ads')
    logger.info('Connecting to: %s BigQuery', GOOGLE_CLOUD_PROJECT)
    client = bigquery.Client(
        project=GOOGLE_CLOUD_PROJECT, credentials=credentials)

    query = f"""
      WITH YouTube AS (
        SELECT
          *
        FROM
          `ads_placement_excluder.*`
        WHERE
          _TABLE_SUFFIX = 'youtube_channels'
      )
      SELECT DISTINCT
        Ads.placement
      FROM
        `ads_placement_excluder.google_ads_placement_report_{customer_id}` AS Ads
      LEFT JOIN
        YouTube USING(placement)
      WHERE
        YouTube.placement IS NULL
    """
    logger.info('Running query: %s', query)
    rows = client.query(query).result()
    channel_ids = []
    for row in rows:
        channel_ids.append(row.placement)
    logger.info('Received %s channel_ids', len(channel_ids))
    return channel_ids


def get_youtube_dataframe(
        channel_ids: List[str],
        credentials: google.auth.credentials.Credentials
) -> None:
    """Pull information on each of the channels provide from the YouTube API.

    The YouTube API only allows pulling up to 50 channels in each request, so
    multiple requests have to be made to pull all the data. See the docs for
    more details:
    https://developers.google.com/youtube/v3/docs/channels/list

    Args:
        channel_ids: the channel IDs to pull the info on from YouTube
        credentials: Google Auth credentials
    """
    logger.info('Getting YouTube data for channel IDs')
    # Maximum number of channels per YouTube request. See:
    # https://developers.google.com/youtube/v3/docs/channels/list
    chunk_size = 50
    chunks = split_list_to_chunks(channel_ids, chunk_size)
    number_of_chunks = len(chunks)

    logger.info('Connecting to the youtube API')
    youtube = build('youtube', 'v3', credentials=credentials)
    is_translated = get_translate_filter(credentials)

    for i, chunk in enumerate(chunks):
        logger.info(f'Processing chunk {i + 1} of {number_of_chunks}')
        chunk_list = list(chunk)
        request = youtube.channels().list(
            part='id, statistics, snippet, brandingSettings',
            id=chunk_list,
            maxResults=chunk_size)
        response = request.execute()
        channels = process_youtube_response(response, chunk_list, is_translated)
        youtube_df = pd.DataFrame(channels, columns=[
            'placement',
            'viewCount',
            'videoCount',
            'subscriberCount',
            'title',
            'title_language',
            'title_language_confidence',
            'country',
            'defaultLanguage',
            'defaultLanguageBrand'
        ])
        youtube_df['datetime_updated'] = datetime.now()
        youtube_df = youtube_df.astype({
            'viewCount': pd.Int64Dtype(),
            'videoCount': pd.Int64Dtype(),
            'subscriberCount': pd.Int64Dtype(),
            'title_language_confidence': 'float',
        })
        write_results_to_bigquery(youtube_df)
    logger.info('YouTube channel info complete')


def split_list_to_chunks(
        lst: List[Any], max_size_of_chunk: int) -> List[np.ndarray]:
    """Split the list into X chunks with the maximum size as specified.

    Args:
        lst: The list to be split into chunks
        max_size_of_chunk: the maximum number of elements that should be in a
            chunk.

    Returns:
        A list containing numpy array chunks of the original list.
    """
    logger.info('Splitting list into chunks')
    num_of_chunks = math.ceil(len(lst) / max_size_of_chunk)
    chunks = np.array_split(lst, num_of_chunks)
    logger.info('Split list into %i chunks', num_of_chunks)
    return chunks


def process_youtube_response(
        response: Dict[str, Any],
        channel_ids: List[str],
        is_translated: bool,
) -> List[List[Any]]:
    """Process the YouTube response to extract the required information.

    Args:
        response: The YouTube channels list response
            https://developers.google.com/youtube/v3/docs/channels/list#response
        channel_ids: A list of the channel IDs passed in the request
        is_translated: A flag showing whether YouTube channel title should be translated or not

    Returns:
        A list of dicts where each dict represents data from one channel
    """
    logger.info('Processing youtube response')
    data = []
    if response.get('pageInfo').get('totalResults') == 0:
        logger.warning('The YouTube response has no results: %s', response)
        logger.warning(channel_ids)
        return data

    for channel in response['items']:
        title = channel.get('snippet').get('title', '')
        if is_translated:
            title_language, confidence = detect_language(title)
        else:
            title_language = ''
            confidence = 0
        data.append([
            channel.get('id'),
            channel.get('statistics').get('viewCount', None),
            channel.get('statistics').get('subscriberCount', None),
            channel.get('statistics').get('videoCount', None),
            title,
            title_language,
            confidence,
            channel.get('snippet').get('country', ''),
            channel.get('snippet').get('defaultLanguage', ''),
            channel.get('brandingSettings').get('defaultLanguage', ''),
        ])
    return data

def get_translate_filter(credentials: google.auth.credentials.Credentials) -> bool:
    """Get the filter for YouTube channel title translation.
    Args:
        credentials: Google Auth credentials

    Returns:
        True if filter is enabled, False otherwise
    """
    logger.info('Getting config from sheet %s', SHEET_ID)

    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet = sheets_service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range='yt_translation_filter').execute().get('values', [['Disabled']])[0][0]

    is_enabled = True if result == 'Enabled' else False
    logger.info('Translation filter enabled is %s', is_enabled)

    return is_enabled


def detect_language(text: str) -> Tuple[str, float]:
    """Detects the text's language.

    Args:
        text: the text to base the translation off of

    Returns:
        A tuple containing the language and the confidence.
    """
    logger.debug('Detecting language for %s', text)
    translate_client = translate.Client()
    result = translate_client.detect_language(text)
    return result['language'], result['confidence']


def write_results_to_bigquery(youtube_df: pd.DataFrame) -> None:
    """Write the YouTube dataframe to BigQuery

    Args:
        youtube_df: the dataframe based on the YouTube data.
    """
    logger.info('Writing the results to BigQuery in: %s', GOOGLE_CLOUD_PROJECT)
    logger.info('There are %s rows', len(youtube_df.index))
    destination_table = f'ads_placement_excluder.youtube_channels'
    logger.info('Destination is: %s', destination_table)
    youtube_df.to_gbq(
        destination_table=destination_table,
        project_id=GOOGLE_CLOUD_PROJECT,
        if_exists='append',
    )


def send_messages_to_pubsub(customer_id: str, sheet_id: str) -> None:
    """Push the customer ID to pub/sub when the job completes.

    Args:
        customer_id: the customer ID to fetch the Google Ads data for.
        sheet_id: the ID of the Google Sheet containing the config.
    """
    logger.info('Sending message to pub/sub for customer_id: %s', customer_id)

    publisher = pubsub_v1.PublisherClient()

    # The `topic_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/topics/{topic_id}`
    logger.info('Publishing to topic: %s', APE_ADS_EXCLUDER_PUBSUB_TOPIC)
    topic_path = publisher.topic_path(
        GOOGLE_CLOUD_PROJECT, APE_ADS_EXCLUDER_PUBSUB_TOPIC)
    logger.info('Full topic path: %s', topic_path)

    message_str = json.dumps({
        'customer_id': customer_id,
        'sheet_id': sheet_id,
    })
    logger.info('Sending message: %s', message_str)
    # Data must be a bytestring
    data = message_str.encode("utf-8")
    publisher.publish(topic_path, data)

    logger.info('Message published')
