# Ads Placement Excluder

## Problem
It is manual and challenging to detect YouTube channel placements which might be
spam (low performance with high cost), and exclude them from future advertising.
Google Ads does not currently provide enough granularity to identify all spam
channels.

## Solution
Based on performance, a client can define what their interpretation of a spam
channel is, and our solution will leverage the Google Ads & YouTube APIs to
automate identifying these placements, and exclude them from future advertising.

## Architecture

The solution is split into the following microservices:

- [Google Ads Reporting Service](./src/services/gads_reporting/README.md)
- [YouTube Channel Service](./src/services/youtube_channel/README.md)
- [Google Ads Exclusion Service](./src/services/gads_exclusion/README.md)
