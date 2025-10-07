import peewee_utils
import pytest
import settings_utils

from fts_exp.conf.settings import settings, test_settings


@pytest.fixture(autouse=True, scope="function")
def test_settings_fixture(monkeypatch, request):
    # Copy all test settings to settings.
    settings_utils.copy_settings(test_settings, settings)


@pytest.fixture(autouse=True, scope="function")
def use_db_fixture(test_settings_fixture):
    # `do_force_new_db_init` is required when running concurrent tests with in-memory
    #  SQLite db.
    with peewee_utils.use_db(do_force_new_db_init=True):
        peewee_utils.create_all_tables()
        yield
