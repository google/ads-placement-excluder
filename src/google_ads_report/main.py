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
"""Output the placement report from Google Ads to BigQuery."""
import base64
import json
from datetime import datetime, timedelta
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple
from google.ads.googleads.client import GoogleAdsClient
import jsonschema
import pandas as pd
from utils import gcs
from utils import pubsub


logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The Google Cloud project containing the GCS bucket
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
# The bucket to write the data to
APE_GCS_DATA_BUCKET = os.environ.get('APE_GCS_DATA_BUCKET')
# The pub/sub topic to send the success message to
APE_YOUTUBE_PUBSUB_TOPIC = os.environ.get('APE_YOUTUBE_PUBSUB_TOPIC')

# The schema of the JSON in the event payload
message_schema = {
    'type': 'object',
    'properties': {
        'sheet_id': {'type': 'string'},
        'customer_id': {'type': 'string'},
        'lookback_days': {'type': 'number'},
        'gads_filters': {'type': 'string'},
    },
    'required': ['sheet_id', 'customer_id', 'lookback_days', 'gads_filters', ]
}


def main(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """The entry point: extract the data from the payload and starts the job.

    The pub/sub message must match the message_schema object above.

    Args:
        event: A dictionary representing the event data payload.
        context: An object containing metadata about the event.
    """
    del context
    logger.info('Google Ads Reporting Service triggered.')
    logger.info('Message: %s', event)
    message = base64.b64decode(event['data']).decode('utf-8')
    logger.info('Decoded message: %s', message)
    message_json = json.loads(message)
    logger.info('JSON message: %s', message_json)

    # Will raise jsonschema.exceptions.ValidationError if the schema is invalid
    jsonschema.validate(instance=message_json, schema=message_schema)

    start_job(
        message_json.get('sheet_id'),
        message_json.get('customer_id'),
        message_json.get('lookback_days'),
        message_json.get('gads_filters'),
    )

    logger.info('Done')


def start_job(
        sheet_id: str,
        customer_id: str,
        lookback_days: int,
        gads_filters: str,
) -> None:
    """Start the job to run the report from Google Ads & output it.

    Args:
        sheet_id: the ID of the Google Sheet containing the config.
        customer_id: the customer ID to fetch the Google Ads data for.
        lookback_days: the number of days from today to look back when fetching
            the report.
        gads_filters: the filters to apply to the Google Ads report query
    """
    logger.info('Starting job to fetch data for %s', customer_id)
    report_df = get_report_df(customer_id, lookback_days, gads_filters)
    write_results_to_gcs(report_df, customer_id)
    send_messages_to_pubsub(customer_id, sheet_id)
    logger.info('Job complete')


def get_report_df(
        customer_id: str,
        lookback_days: int,
        gads_filters: str) -> pd.DataFrame:
    """Run the placement report in Google Ads & return a Dataframe of the data.

    Args:
        customer_id: the customer ID to fetch the Google Ads data for.
        lookback_days: the number of days from today to look back when fetching
            the report.
        gads_filters: the filters to apply to the Google Ads report query

    Returns:
        A Pandas DataFrame containing the report results.
    """
    logger.info('Getting report stream for %s', customer_id)
    now = datetime.now()
    client = GoogleAdsClient.load_from_env(version='v11')
    ga_service = client.get_service("GoogleAdsService")

    query = get_report_query(lookback_days, gads_filters)
    search_request = client.get_type("SearchGoogleAdsStreamRequest")
    search_request.customer_id = customer_id
    search_request.query = query
    stream = ga_service.search_stream(search_request)

    # The client and iterator needs to be in the same function, as per
    # https://github.com/googleads/google-ads-python/issues/384#issuecomment-791639397
    # So this can't be refactored out
    logger.info('Processing response stream')
    data = []
    for batch in stream:
        for row in batch.results:
            data.append([
                now,
                row.customer.id,
                row.group_placement_view.placement,
                row.group_placement_view.target_url,
                row.metrics.impressions,
                row.metrics.cost_micros,
                row.metrics.conversions,
                row.metrics.video_view_rate,
                row.metrics.video_views,
                row.metrics.clicks,
                row.metrics.average_cpm,
                row.metrics.ctr,
                row.metrics.all_conversions_from_interactions_rate,
            ])
    return pd.DataFrame(data, columns=[
        'datetime_updated',
        'customer_id',
        'channel_id',
        'placement_target_url',
        'impressions',
        'cost_micros',
        'conversions',
        'video_view_rate',
        'video_views',
        'clicks',
        'average_cpm',
        'ctr',
        'all_conversions_from_interactions_rate',
    ])


def get_report_query(lookback_days: int,
                     gads_filters: Optional[str] = None) -> str:
    """Build and return the Google Ads report query.

    Args:
        lookback_days: the number of days from today to look back when fetching
            the report.
        gads_filters: the filters to apply to the Google Ads report query

    Return:
        The Google Ads query.
    """
    logger.info('Getting report query')
    date_from, date_to = get_query_dates(lookback_days)
    where_query = ''
    if gads_filters is not None:
        where_query = f'AND {gads_filters}'
    query = f"""
        SELECT
            customer.id,
            group_placement_view.placement,
            group_placement_view.target_url,
            metrics.impressions,
            metrics.cost_micros,
            metrics.conversions,
            metrics.video_views,
            metrics.video_view_rate,
            metrics.clicks,
            metrics.average_cpm,
            metrics.ctr,
            metrics.all_conversions_from_interactions_rate
        FROM
            group_placement_view
        WHERE group_placement_view.placement_type = "YOUTUBE_CHANNEL"
            AND campaign.advertising_channel_type = "VIDEO"
            AND segments.date BETWEEN "{date_from}" AND "{date_to}"
            {where_query}
    """
    logger.info(query)
    return query


def get_query_dates(lookback_days: int,
                    today: datetime = None) -> Tuple[str, str]:
    """Return a tuple of string dates in %Y-%m-%d format for the GAds report.

    Google Ads queries require a string date in the above format. This function
    will lookback X days from today, and return this date as a string.

    Args:
        lookback_days: the number of days from today to look back when fetching
            the report.
        today: the date representing today. If no date is provided
            datetime.today() is used.

    Return:
        The string date
    """
    logger.info('Getting query dates')
    dt_format = '%Y-%m-%d'
    if today is None:
        today = datetime.today()
    date_from = today - timedelta(days=lookback_days)
    return (
        date_from.strftime(dt_format),
        today.strftime(dt_format),
    )


def write_results_to_gcs(report_df: pd.DataFrame, customer_id: str) -> None:
    """Write the report dataframe to GCS as a CSV file

    Args:
        report_df: the dataframe based on the Google Ads report.
        customer_id: the customer ID to fetch the Google Ads data for.
    """
    logger.info('Writing results to GCS: %s', APE_GCS_DATA_BUCKET)
    number_of_rows = len(report_df.index)
    logger.info('There are %s rows', number_of_rows)
    if number_of_rows > 0:
        blob_name = f'google_ads_report/{customer_id}.csv'
        logger.info('Blob name: %s', blob_name)
        gcs.upload_blob_from_df(
            df=report_df,
            blob_name=blob_name,
            bucket=APE_GCS_DATA_BUCKET)
        logger.info('Blob uploaded to GCS')
    else:
        logger.info('There is nothing to write to GCS')


def send_messages_to_pubsub(customer_id: str, sheet_id: str) -> None:
    """Push the customer ID to pub/sub when the job completes.

    Args:
        customer_id: the customer ID to fetch the Google Ads data for.
        sheet_id: the ID of the Google Sheet containing the config.
    """
    message_dict = {
        'customer_id': customer_id,
        'sheet_id': sheet_id,
    }
    logger.info('Sending message to pub/sub:', message_dict)
    pubsub.send_dict_to_pubsub(
        message_dict=message_dict,
        topic=APE_YOUTUBE_PUBSUB_TOPIC,
        gcp_project=GOOGLE_CLOUD_PROJECT)
    logger.info('Message published')
