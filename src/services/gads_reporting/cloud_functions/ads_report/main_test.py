"""Unit tests for main.py"""
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch
import main


class MainTestCase(unittest.TestCase):

    @patch('main.start_job')
    def test_main(self, mock_start_job):
        mock_request = MagicMock()
        mock_request.get_json.return_value = {}
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 400)
        mock_start_job.assert_not_called()

        mock_request.get_json.return_value = {'customer_id': '123'}
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 400)
        mock_start_job.assert_not_called()

        mock_request.get_json.return_value = {'lookback_days': 90}
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 400)
        mock_start_job.assert_not_called()

        mock_request.get_json.return_value = {
            'customer_id': '123',
            'lookback_days': 90,
        }
        response = main.main(mock_request)
        self.assertEqual(response.status_code, 200)
        mock_start_job.assert_called_once()

    def test_get_query_dates(self):
        today_str = '2022-07-01'
        today = datetime.strptime(today_str, '%Y-%m-%d')
        date_from, date_to = main.get_query_dates(90, today)
        self.assertEqual(date_to, today_str)
        self.assertEqual(date_from, '2022-04-02')


if __name__ == '__main__':
    unittest.main()
