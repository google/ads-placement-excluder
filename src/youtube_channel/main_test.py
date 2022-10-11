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
import numpy as np
import pandas as pd
import main


class MainTestCase(unittest.TestCase):

    def test_sanitise_youtube_dataframe(self):
        columns = [
            'title',
            'view_count',
            'video_count',
            'subscriber_count',
            'title_language_confidence',
        ]
        raw_data = [
            ['String with a new line \n', '10', '1', '3', '0.56'],
            ['String, with, commas in,it', '10', '1', '3', '0.56'],
            ['String with "double quotes" in it', '10', '1', '3', '0.56'],
            ["String with 'single quotes' in it", '10', '1', '3', '0.56'],
            ['  String with white space    ', '10', '1', '3', '0.56'],
            ['String with $\r\t\n;:,', '10', '1', '3', '0.56'],
            ['Строка написана на русском языке', '10', '1', '3', '0.56'],
            ['用中文寫的字符串', '10', '1', '3', '0.56'],
        ]
        expected_data = [
            ['String with a new line', 10, 1, 3, 0.56],
            ['String with commas init', 10, 1, 3, 0.56],
            ['String with double quotes in it', 10, 1, 3, 0.56],
            ['String with single quotes in it', 10, 1, 3, 0.56],
            ['String with white space', 10, 1, 3, 0.56],
            ['String with', 10, 1, 3, 0.56],
            ['Строка написана на русском языке', 10, 1, 3, 0.56],
            ['用中文寫的字符串', 10, 1, 3, 0.56],
        ]
        raw_df = pd.DataFrame(data=raw_data, columns=columns)
        expected_df = pd.DataFrame(data=expected_data, columns=columns)
        response_df = main.sanitise_youtube_dataframe(raw_df)
        pd.testing.assert_frame_equal(expected_df, response_df)

    def test_split_list_to_chunks(self):
        lst = np.arange(150)
        max_chunk_size = 50
        chunks = main.split_list_to_chunks(lst, max_chunk_size)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)
        self.assertEqual(len(chunks[2]), 50)

        lst = np.arange(151)
        max_chunk_size = 50
        chunks = main.split_list_to_chunks(lst, max_chunk_size)
        self.assertEqual(len(chunks), 4)
        self.assertTrue(len(chunks[0]) < 50)
        self.assertTrue(len(chunks[1]) < 50)
        self.assertTrue(len(chunks[2]) < 50)
        self.assertTrue(len(chunks[3]) < 50)
