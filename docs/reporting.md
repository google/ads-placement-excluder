# Ads Placement Excluder Reporting

There is a DataStudio dashboard that can be used to monitor the behaviour of the
solution, and identify which channels are being excluded.

![Google Ads Account Architecture Diagram](
./images/ape-datastudio-report-example.png)

## Get Started

1. Make a copy of the template from [here](
   https://datastudio.google.com/reporting/4a616bed-85e9-4794-a748-721051c10755)
   to your Drive folder
2. While copying choose `ViewExclusions` as a new data source. `ViewExclusions`
   view will be created automatically by Terraform after the first deployment.
   a. If `ViewExclusions` does not appear in available data sources you need to
   Create Data Source -> Big Query -> Your Project and find `ViewExclusions`
   table there b. You can also add a custom data source to each chart in a chart
   setup tab afterwards
3. Sometimes `customer_id` is auto-defined as a date leading to the chart
   configuration error. You can change the field type manually to number via
   Resource -> Manage Data Sources -> Edit
4. You can adjust charts and filters according to your needs

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
