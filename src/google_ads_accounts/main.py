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
"""Fetch the Google Ads configs and push them to pub/sub."""
import json
import logging
import os
import sys
from typing import Any, List, Dict
import flask
import google.auth
from google.cloud import pubsub_v1
from googleapiclient.discovery import build
import jsonschema


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The Google Cloud project containing the pub/sub topic
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
# The name of the pub/sub topic
APE_ADS_REPORT_PUBSUB_TOPIC = os.environ.get('APE_ADS_REPORT_PUBSUB_TOPIC')
# The access scopes used in this function
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
# The range in the sheet containing the config data
SHEET_RANGE = 'Google Ads!A2:D'

# The schema of the JSON in the request
request_schema = {
    'type': 'object',
    'properties': {
        'sheet_id': {'type': 'string'},
    },
    'required': ['sheet_id', ]
}


def main(request: flask.Request) -> flask.Response:
    """The entry point: extract the data from the payload and starts the job.

    The request payload must match the request_schema object above.

    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The flask response.
    """
    logger.info('Google Ads Account Service triggered.')
    request_json = request.get_json()
    logger.info('JSON payload: %s', request_json)
    response = {}
    try:
        jsonschema.validate(instance=request_json, schema=request_schema)
    except jsonschema.exceptions.ValidationError as err:
        logger.error('Invalid request payload: %s', err)
        response['status'] = 'Failed'
        response['message'] = err.message
        return flask.Response(flask.json.dumps(response),
                              status=400,
                              mimetype='application/json')

    run(request_json['sheet_id'])

    response['status'] = 'Success'
    response['message'] = 'Downloaded data successfully'
    return flask.Response(flask.json.dumps(response),
                          status=200,
                          mimetype='application/json')


def run(sheet_id: str) -> None:
    """Orchestration for the function.

    Args:
        sheet_id: the ID of the Google Sheet containing the config.
    """
    logger.info('Running Google Ads account script')
    account_configs = get_config_from_sheet(sheet_id)
    send_messages_to_pubsub(account_configs)
    logger.info('Done.')


def get_config_from_sheet(sheet_id: str) -> List[Dict[str, Any]]:
    """Get the Ads account config from the Google Sheet, and return the results.

    Args:
        sheet_id: the ID of the Google Sheet containing the config.

    Returns:
        Returns a row for each account a report needs to be run for.

        [
            {
                'customer_id': '1234567890'
                'lookback_days': 90,
                'gads_filters': 'metrics.clicks > 10',
            },
            ...
        ]
    """
    logger.info('Getting config from sheet: %s', sheet_id)
    credentials, project_id = google.auth.default(scopes=SCOPES)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id,
                                range=SHEET_RANGE).execute()
    rows = result.get('values', [])
    logger.info('Returned %i rows', len(rows))

    account_configs = []
    for row in rows:
        if row[3] == 'Enabled':
            account_configs.append({
                'customer_id': row[0],
                'lookback_days': int(row[1]),
                'gads_filters': row[2],
            })
        else:
            logger.info('Ignoring disabled row: %s', row)

    logger.info('Account configs:')
    logger.info(account_configs)
    return account_configs


def send_messages_to_pubsub(messages: List[Dict[str, Any]]) -> None:
    """Push each of the messages to the pubsub topic.

    Args:
        messages: the list of messages to push to pubsub
    """
    logger.info('Sending messages to pubsub')
    logger.info('Messages: %s', messages)
    publisher = pubsub_v1.PublisherClient()

    # The `topic_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/topics/{topic_id}`
    logger.info('Publishing to topic: %s', APE_ADS_REPORT_PUBSUB_TOPIC)
    topic_path = publisher.topic_path(GOOGLE_CLOUD_PROJECT, APE_ADS_REPORT_PUBSUB_TOPIC)
    logger.info('Full topic path: %s', topic_path)

    for message in messages:
        message_str = json.dumps(message)
        logger.info('Sending message: %s', message_str)
        # Data must be a bytestring
        data = message_str.encode("utf-8")
        publisher.publish(topic_path, data)

    logger.info('All messages published')
