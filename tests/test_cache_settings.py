from django.test import SimpleTestCase

from bufia.settings import CACHES, USE_DB_CACHE


class CacheSettingsTests(SimpleTestCase):
    def test_default_cache_backend_is_locmem_unless_db_cache_is_enabled(self):
        expected_backend = (
            'django.core.cache.backends.db.DatabaseCache'
            if USE_DB_CACHE
            else 'django.core.cache.backends.locmem.LocMemCache'
        )

        self.assertEqual(CACHES['default']['BACKEND'], expected_backend)
