# Google Ads Account Function

This function pulls the list of Google Accounts to fetch the report data for,
from a Google Sheet. Once the list has been pulled, it pushes each account as a
message to a Pub/sub topic, which triggers the Ads Report function.

To run the code ensure the following environment variables are set:

```
export GOOGLE_CLOUD_PROJECT=ads-placement-excluder
export APE_ADS_REPORT_PUBSUB_TOPIC=ads-report-topic
```

Ensure that the Google Sheet has been shared with the service account that was
created.

## Local Deployment

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

Next set the environment variables above and install the dev
requirements:

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
