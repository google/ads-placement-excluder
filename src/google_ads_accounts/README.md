# Google Ads Account Function

This service is responsible for deciding which Google Ads accounts the Ads
Placement Excluder solution should run for, and kicking off the downstream
pipeline. Each account is pushed as a separate message into the topic to enable
concurrency.

## Local Deployment
To run the code ensure the following environment variables are set:

```
export GOOGLE_CLOUD_PROJECT=ads-placement-excluder
export APE_ADS_REPORT_PUBSUB_TOPIC=ads-report-topic
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
  --scopes='https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/cloud-platform' \
  --client-id-file=/path/to/client-id-file.json
```
[Optionally] [see this article](
https://medium.com/google-cloud/google-oauth-credential-going-deeper-the-hard-way-f403cf3edf9d)
for a detailed explanation, why this is needed.

Next install the dev requirements:

```
pip install -r requirements_dev.txt
```

Then start the server by running:

```
functions-framework --target=main --port=8080
```

You can then make a post request by running the following:

```
curl localhost:8080 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"sheet_id": "12g3IoIP4Lk_UU3xtJsIiCSDxjNAn30vT4lOzSZPS-mk"}'
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
