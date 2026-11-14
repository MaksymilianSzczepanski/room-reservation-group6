from unittest.mock import patch

from django.test import SimpleTestCase


class SearchAPITests(SimpleTestCase):
    @patch("microservices.search.views.call")
    def test_filters_occupied_rooms(self, remote):
        remote.side_effect = [[{"id": 1}, {"id": 2}], [1]]
        result = self.client.get("/api/search/?start=2026-10-19T09%3A00%3A00%2B02%3A00&end=2026-10-19T10%3A00%3A00%2B02%3A00")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), [{"id": 2}])
