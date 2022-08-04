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
from datetime import datetime, timedelta
import logging
import os
import sys
from typing import Tuple
import flask
from google.ads.googleads.client import GoogleAdsClient
import jsonschema
import pandas as pd

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

# TODO(b/241376573): add filters for Google Ads Report
request_schema = {
    'type': 'object',
    'properties': {
        'customer_id': {'type': 'string'},
        'lookback_days': {'type': 'number'},
    },
    'required': ['customer_id', 'lookback_days']
}


def main(request: flask.Request) -> flask.Response:
    """The entry point: extract the data from the payload and starts the job.

    The request payload must match the request_schema object above.

    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The flask response.
    """
    logger.info('Google Ads Reporting Service triggered.')
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

    start_job(
        request_json.get('customer_id'),
        request_json.get('lookback_days'))

    response['status'] = 'Success'
    response['message'] = 'Downloaded data successfully'
    return flask.Response(flask.json.dumps(response),
                          status=200,
                          mimetype='application/json')


def start_job(customer_id: str, lookback_days: int = 90) -> None:
    """Start the job to run the report from Google Ads & output it.

    Args:
        customer_id: the customer ID to fetch the Google Ads data for.
        lookback_days: the number of days from today to look back when fetching
            the report.
    """
    logger.info('Starting job to fetch data for %s', customer_id)
    report_df = get_report_df(customer_id, lookback_days)
    write_results_to_bigquery(report_df, customer_id)
    logger.info('Job complete')


def get_report_df(
        customer_id: str,
        lookback_days: int) -> pd.DataFrame:
    """Run the placement report in Google Ads & return a Dataframe of the data.

    Args:
        customer_id: the customer ID to fetch the Google Ads data for.
        lookback_days: the number of days from today to look back when fetching
            the report.

    Returns:
        A Pandas DataFrame containing the report results.
    """
    logger.info('Getting report stream for %s', customer_id)
    client = GoogleAdsClient.load_from_env(version='v11')
    ga_service = client.get_service("GoogleAdsService")

    query = get_report_query(lookback_days)
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
        'customer_id',
        'placement',
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


def get_report_query(lookback_days: int) -> str:
    """Build and return the Google Ads report query.

    Args:
        lookback_days: the number of days from today to look back when fetching
            the report.

    Return:
        The Google Ads query.
    """
    logger.info('Getting report query')
    date_from, date_to = get_query_dates(lookback_days)
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


def write_results_to_bigquery(report_df: pd.DataFrame,
                              customer_id: str) -> None:
    """Write the report dataframe to BigQuery

    Args:
        report_df: the dataframe based on the Google Ads report.
        customer_id: the customer ID to fetch the Google Ads data for.
    """
    logger.info('Writing the results to BigQuery in: %s', GOOGLE_CLOUD_PROJECT)
    logger.info('There are %s rows', len(report_df.index))
    destination_table = f'ads_placement_excluder.google_ads_placement_report_{customer_id}'
    logger.info('Destination is: %s', destination_table)
    report_df.to_gbq(
        destination_table=destination_table,
        project_id=GOOGLE_CLOUD_PROJECT,
        if_exists='replace',
    )
