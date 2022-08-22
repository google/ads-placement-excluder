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
"""Unit tests for main.py"""
import unittest
from unittest.mock import MagicMock, patch
import main


class MainTestCase(unittest.TestCase):

    @patch('main.run')
    def test_main(self, mock_run):
        mock_request = MagicMock()
        mock_request.get_json.return_value = {}
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 400)
        mock_run.assert_not_called()
        mock_request.get_json.return_value = {
            'sheet_id': '12345',
        }
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 200)
        mock_run.assert_called_once()

    def test_gads_filters_to_sql_string(self):
        config_filters = [['impressions', '>', '1']]
        gaql = main.gads_filters_to_gaql_string(config_filters)
        self.assertEqual(gaql, 'metrics.impressions > 1')

        config_filters = [['impressions', '>', '1'], ['clicks', '<', '50']]
        gaql = main.gads_filters_to_gaql_string(config_filters)
        self.assertEqual(gaql,
                         'metrics.impressions > 1 AND metrics.clicks < 50')


if __name__ == '__main__':
    unittest.main()
