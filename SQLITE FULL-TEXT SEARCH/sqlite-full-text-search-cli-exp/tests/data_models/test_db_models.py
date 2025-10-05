from datetime import timedelta, timezone

from fts_exp.data_models.db_models import ItemModel


class TestItemModel:
    def test_create(self):
        assert ItemModel.select().count() == 0
        ItemModel.create(title="My first title", notes="My first note")
        ItemModel.create(title="My second title", notes="My second note")
        assert ItemModel.select().count() == 2

    def test_db_isolation(self):
        # It's intentionally the same as the prev test. The purpose is to ensure that
        #  single tests isolation works and the 2 items inserted in the prev tests are
        #  gone.
        assert ItemModel.select().count() == 0
        ItemModel.create(title="My first title", notes="My first note")
        ItemModel.create(title="My second title", notes="My second note")
        assert ItemModel.select().count() == 2

    def test_updated_at(self):
        ItemModel.create(title="My first title", notes="My first note")

        # The goal is to ensure that when updating an ItemModel, then its `updated_at`
        #  attribute is automatically updated.
        a = ItemModel.get_by_id(1)
        assert a.created_at.tzinfo == timezone.utc
        assert a.updated_at > a.created_at
        assert (a.updated_at - a.created_at) > timedelta(seconds=0)
        assert (a.updated_at - a.created_at) < timedelta(seconds=1)

        prev_updated_at = a.updated_at
        new_title = "title bis"
        a.title = new_title
        a.save()
        # Reload the model to get the new updated_at.
        a = ItemModel.get_by_id(1)
        assert a.title == new_title
        assert a.updated_at > prev_updated_at
        assert (a.updated_at - prev_updated_at) > timedelta(seconds=0)
        assert (a.updated_at - prev_updated_at) < timedelta(seconds=1)
