# YouTube Channel Reporting Service

This service pulls the YouTube placements ids from BigQuery and enriches
placements data with YouTube data.

To run the code ensure the following environment variables are set:

```
export GOOGLE_CLOUD_PROJECT=
```

## Google Translate API

TODO: write me... cost $20 per million characters

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
  --scopes='https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/youtube' \
  --client-id-file=/path/to/client-id-file.json
```
[Optionally] [see this article](
https://medium.com/google-cloud/google-oauth-credential-going-deeper-the-hard-way-f403cf3edf9d)
for a detailed explanation, why this is needed.

Next set the environment variables above and install the dev requirements:

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
  -d "{ \"data\": { \"data\": \"$(echo '{ "customer_id": "1234567890" }' | base64)\" }}"
```