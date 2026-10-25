from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigrationTestCase(TransactionTestCase):
    def migrate(self, *targets):
        executor = MigrationExecutor(connection)
        executor.migrate(list(targets))

        return executor.loader.project_state(list(targets)).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
