from django.test import SimpleTestCase

from bufia.settings import _normalize_database_url


class DatabaseUrlNormalizationTests(SimpleTestCase):
    def test_external_render_postgres_url_gets_sslmode_require(self):
        original = (
            'postgresql://bufia:secret@'
            'dpg-d7kdhd5f420s73a6048g-a.singapore-postgres.render.com/'
            'bufia_92fv'
        )

        normalized = _normalize_database_url(original)

        self.assertEqual(
            normalized,
            original + '?sslmode=require',
        )

    def test_existing_query_uses_ampersand(self):
        original = (
            'postgresql://bufia:secret@'
            'dpg-d7kdhd5f420s73a6048g-a.singapore-postgres.render.com/'
            'bufia_92fv?connect_timeout=10'
        )

        normalized = _normalize_database_url(original)

        self.assertIn('connect_timeout=10', normalized)
        self.assertIn('sslmode=require', normalized)
        self.assertIn('&', normalized)

    def test_existing_sslmode_is_preserved(self):
        original = (
            'postgresql://bufia:secret@'
            'dpg-d7kdhd5f420s73a6048g-a.singapore-postgres.render.com/'
            'bufia_92fv?sslmode=verify-full'
        )

        self.assertEqual(_normalize_database_url(original), original)

    def test_non_render_url_is_unchanged(self):
        original = 'postgresql://bufia:secret@localhost:5432/bufia_92fv'

        self.assertEqual(_normalize_database_url(original), original)
