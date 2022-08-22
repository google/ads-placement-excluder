# Google Ads Reporting Service

This service is responsible for running a report from Google Ads based on the
[group_placement_view](
https://developers.google.com/google-ads/api/fields/v11/group_placement_view),
with the configured filters, and outputting that as a CSV to a Cloud Storage
bucket, with a BigQuery table in front of it. The data pulled from the report is
filtered to only have YouTube channels.

## Local Deployment
To run the code ensure the following environment variables are set:

```
export GOOGLE_ADS_USE_PROTO_PLUS=false
export GOOGLE_ADS_REFRESH_TOKEN=
export GOOGLE_ADS_CLIENT_ID=
export GOOGLE_ADS_CLIENT_SECRET=
export GOOGLE_ADS_DEVELOPER_TOKEN=
export GOOGLE_ADS_LOGIN_CUSTOMER_ID=
export GOOGLE_CLOUD_PROJECT=
export APE_YOUTUBE_PUBSUB_TOPIC=
export APE_GCS_DATA_BUCKET=
```

Next install the dev requirements:

```
pip install -r requirements_dev.txt
```

Then start the server by running:

```
functions-framework --target=main --signature-type=event --port=8080
```

You can then make a post request by running the following:

```
curl localhost:8080 \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{ \"data\": { \"data\": \"$(echo '{ "customer_id": "1234567890", "lookback_days": 90, "gads_filters": "metrics.impressions > 0", "sheet_id": "abcdefghijklmnop-mk"}' | base64)\" }}"
```

### Mac users

You may need to set this environment variable for the Google Ads report stream
to work, [see Github for more info](https://github.com/rails/rails/issues/38560).

```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

## Disclaimers
__This is not an officially supported Google product.__

Copyright 2022 Google LLC. This solution, including any related sample code or
data, is made available on an “as is,” “as available,” and “with all faults”
basis, solely for illustrative purposes, and without warranty or representation
of any kind. This solution is experimental, unsupported and provided solely for
your convenience. Your use of it is subject to your agreements with Google, as
applicable, and may constitute a beta feature as defined under those agreements.
To the extent that you make any data available to Google in connection with your
use of the solution, you represent and warrant that you have all necessary and
appropriate rights, consents and permissions to permit Google to use and process
that data. By using any portion of this solution, you acknowledge, assume and
accept all risks, known and unknown, associated with its usage, including with
respect to your deployment of any portion of this solution in your systems, or
usage in connection with your business, if at all.
