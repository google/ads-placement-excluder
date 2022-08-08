from googleapiclient.discovery import build
from google.cloud import bigquery
import pydata_google_auth
import pandas as pd
import sys
import logging

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
API_KEY = ''
GOOGLE_CLOUD_PROJECT = 'ads-placement-excluder'
credentials = pydata_google_auth.get_user_credentials(
    ['https://www.googleapis.com/auth/cloud-platform'],
)
CHUNK = 50

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    placements = get_placements_query()
    youtube_df = get_youtube_dataframe(placements)
    report = add_customer_id(youtube_df, placements)
    write_results_to_bigquery(report)
    print('done')


def get_placements_query():
    logger.info('Connecting to: %s BigQuery', GOOGLE_CLOUD_PROJECT)
    client = bigquery.Client(project=GOOGLE_CLOUD_PROJECT, credentials=credentials)

    logger.info('Getting placement data of all clients')
    query = """
      SELECT customer_id, placement
      FROM `ads_placement_excluder.google_ads_placement_report_*`
  """
    rows = list(client.query(query).result())
    ids = []

    for row in rows:
        ids.append([
            row.customer_id,
            row.placement,
        ])
    logger.info('Received %s rows', len(ids))
    return ids


def get_youtube_dataframe(placements: []) -> pd.DataFrame:
    logger.info('Connecting to: %s API', API_SERVICE_NAME)
    youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)

    logger.info('Retrieving placement ids and getting rid of duplicates')
    placement_ids = [*set([row[1] for row in placements])]
    i = 0
    channels = []

    logger.info('Extracting data from %s API in chunks (%s entries per chunk)', API_SERVICE_NAME, CHUNK)
    while i < len(placement_ids):
        ids = placement_ids[i:i + CHUNK]
        request = youtube.channels().list(part='id, statistics, snippet, brandingSettings', id=ids, maxResults=CHUNK)
        response = request.execute()
        channels.extend(get_youtube_data_chunks(response, i))
        i += CHUNK

    logger.info('Building a YouTube report')
    return pd.DataFrame(channels, columns=[
        'placement_id',
        'viewCount',
        'videoCount',
        'subscriberCount',
        'title',
        'country',
        'defaultLanguage',
        'defaultLanguageBrand'
    ])


def get_youtube_data_chunks(response: dict, i: int) -> []:
    data = []
    logger.info('Getting data: from %s to %s', i, i + 50)
    for x in response["items"]:
        data.append([
            x.get('id'),
            x.get('statistics').get('viewCount', None),
            x.get('statistics').get('subscriberCount', None),
            x.get('statistics').get('videoCount', None),
            x.get('snippet').get('title', ""),
            x.get('snippet').get('country', ""),
            x.get('snippet').get('defaultLanguage', ""),
            x.get('brandingSettings').get('defaultLanguage', ""),
        ])
    return data


def add_customer_id(youtube_df: pd.DataFrame,
                    placements: []) -> pd.DataFrame:
    logger.info('Adding customer ids to the report')
    placements_df = pd.DataFrame(placements, columns=[
        'customer_id',
        'placement_id',
    ])
    return pd.merge(placements_df, youtube_df, how='outer', on='placement_id')


def write_results_to_bigquery(youtube_df: pd.DataFrame) -> None:
    """Write the YouTube dataframe to BigQuery

    Args:
        youtube_df: the dataframe based on the YouTube data.
    """
    logger.info('Writing the results to BigQuery in: %s', GOOGLE_CLOUD_PROJECT)
    logger.info('There are %s rows', len(youtube_df.index))
    destination_table = 'ads_placement_excluder.google_youtube_channel_report'
    logger.info('Destination is: %s', destination_table)
    youtube_df.to_gbq(
        destination_table=destination_table,
        project_id=GOOGLE_CLOUD_PROJECT,
        if_exists='replace',
    )


if __name__ == '__main__':
    main()
