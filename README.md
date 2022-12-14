# Ads Placement Excluder

It is manual and challenging to detect YouTube channel placements which might be
spam (low performance with high cost), and exclude them from future advertising.
Google Ads does not currently provide enough granularity to identify all spam
channels.

Ads Placement Excluder allows an advertiser, to define what their interpretation
of a spam channel is, and it will leverage the Google Ads & YouTube APIs to
automate identifying these placements, and exclude them from future advertising.

## Architecture
See [architecture.md](./docs/architecture.md).

## Reporting
The solution provides a DataStudio dashboard to monitor the solution. See
[reporting.md](./docs/reporting.md) for more information.

## Get Started
See [deployment.md](./docs/deployment.md) for information on how to deploy the
solution and get started.

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
