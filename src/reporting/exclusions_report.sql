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

-- Remove duplicate rows from YouTube, pulling only the last updated data
WITH
  YouTube AS (
    SELECT *
    FROM `${BQ_DATASET}.YouTubeChannel`
    WHERE true
    QUALIFY ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY datetime_updated DESC) = 1
  )
SELECT DISTINCT
  Excluded.datetime_updated AS excluded_datetime,
  Excluded.channel_id,
  Ads.placement_target_url,
  Excluded.customer_id,
  YouTube.view_count,
  YouTube.video_count,
  YouTube.subscriber_count,
  YouTube.title,
  YouTube.title_language,
  YouTube.title_language_confidence,
  YouTube.country,
  Ads.impressions,
  Ads.cost_micros,
  Ads.conversions,
  Ads.video_view_rate,
  Ads.video_views,
  Ads.clicks,
  Ads.average_cpm,
  Ads.ctr,
  Ads.all_conversions_from_interactions_rate,
FROM
  `${BQ_DATASET}.GoogleAdsExclusion` AS Excluded
LEFT JOIN
  YouTube USING (channel_id)
LEFT JOIN
  `${BQ_DATASET}.GoogleAdsReport` AS Ads
  USING (channel_id, customer_id)
