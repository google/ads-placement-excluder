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
