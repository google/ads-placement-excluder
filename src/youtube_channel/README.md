# YouTube Channel Reporting Service

This service is responsible for pulling metrics about the YouTube channels from
the Google Ads Report. For example the number of views the channel has had, and
the number of subscribers. It then uses the Google Translate API (if enabled in
the config), to determine the language the YouTube channel title is in.

## Google Translate API
This service leverages [Google's Translation API](
https://cloud.google.com/translate/docs/basic/detecting-language), for detecting
the language of the YouTube channel's title.

This is enabled/disabled in the configuration Google Sheet. See the
[basic pricing](https://cloud.google.com/translate/pricing) for cost
information.

## Local Deployment
To run the code ensure the following environment variables are set:

```
export GOOGLE_CLOUD_PROJECT=
export APE_BIGQUERY_DATASET=
export APE_GCS_DATA_BUCKET=
```

The code uses [Google Application Default credentials](
https://google-auth.readthedocs.io/en/master/reference/google.auth.html) for
auth.

First create OAuth desktop credentials in Google Cloud, and download the client
ID and client secret as a JSON file.

Then run the following command, updating the path to point to the JSON file
downloaded in the previous step:
```
gcloud auth application-default login \
  --scopes='https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/youtube' \
  --client-id-file=/path/to/client-id-file.json
```
[Optionally] [see this article](
https://medium.com/google-cloud/google-oauth-credential-going-deeper-the-hard-way-f403cf3edf9d)
for a detailed explanation, why this is needed.

Next install the dev requirements:

```
pip install -r requirements_dev.txt
```

Start the function:

```
functions-framework --target=main --signature-type=event --port=8080
```

You can then make a post request by running the following:

```
curl localhost:8080 \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{ \"data\": { \"data\": \"$(echo '{ "customer_id": "1234567890", "sheet_id": "abcdefghijklmnop-mk" }' | base64)\" }}"
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
