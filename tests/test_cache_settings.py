from django.test import SimpleTestCase

from bufia.settings import CACHES, SESSION_ENGINE, USE_DB_CACHE, USE_DB_SESSIONS


class CacheSettingsTests(SimpleTestCase):
    def test_default_cache_backend_is_locmem_unless_db_cache_is_enabled(self):
        expected_backend = (
            'django.core.cache.backends.db.DatabaseCache'
            if USE_DB_CACHE
            else 'django.core.cache.backends.locmem.LocMemCache'
        )

        self.assertEqual(CACHES['default']['BACKEND'], expected_backend)

    def test_default_session_engine_uses_signed_cookies_unless_db_sessions_are_enabled(self):
        expected_engine = (
            'django.contrib.sessions.backends.db'
            if USE_DB_SESSIONS
            else 'django.contrib.sessions.backends.signed_cookies'
        )

        self.assertEqual(SESSION_ENGINE, expected_engine)
