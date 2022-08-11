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


if __name__ == '__main__':
    unittest.main()
