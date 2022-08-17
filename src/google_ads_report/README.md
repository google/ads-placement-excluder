# Google Ads Reporting Service

This service pulls the placement report from Google Ads and writes it to
BigQuery.

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
```

## Local Deployment

To run the code locally set the environment variables above and install the dev
requirements:

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
