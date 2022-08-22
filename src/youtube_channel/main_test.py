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
import main


class MainTestCase(unittest.TestCase):

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
