"""Unit tests for main.py"""
import base64
from datetime import datetime
import json
from typing import Any, Dict
import unittest
from unittest.mock import patch
import jsonschema
import main


class MainTestCase(unittest.TestCase):

    def _create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """A helper function for creating mock event data.

        Args:
            data: a dictionary containing the event data.
        """
        return {
            'data': base64.b64encode(json.dumps(data).encode('utf-8'))
        }

    @patch('main.start_job')
    def test_main(self, mock_start_job):
        event = self._create_event({'abc': '123'})
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            main.main(event, {})
        mock_start_job.assert_not_called()

        event = self._create_event({'customer_id': '123'})
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            main.main(event, {})
        mock_start_job.assert_not_called()

        event = self._create_event({'lookback_days': 90})
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            main.main(event, {})
        mock_start_job.assert_not_called()

        event = self._create_event({'customer_id': '123', 'lookback_days': 90})
        main.main(event, {})
        mock_start_job.assert_called_once()


    def test_get_query_dates(self):
        today_str = '2022-07-01'
        today = datetime.strptime(today_str, '%Y-%m-%d')
        date_from, date_to = main.get_query_dates(90, today)
        self.assertEqual(date_to, today_str)
        self.assertEqual(date_from, '2022-04-02')


if __name__ == '__main__':
    unittest.main()