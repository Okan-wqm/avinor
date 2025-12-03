# shared/common/db_routers.py
"""
Database Routers for Read Replica Support
"""

import random
from typing import Optional


class ReadReplicaRouter:
    """
    Database router that directs read operations to replica databases
    and write operations to the primary database.
    """

    def db_for_read(self, model, **hints) -> str:
        """
        Direct read operations to replica if available.
        """
        # Check if replica is configured
        from django.conf import settings
        if 'replica' in settings.DATABASES:
            return 'replica'
        return 'default'

    def db_for_write(self, model, **hints) -> str:
        """
        Direct all write operations to primary database.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints) -> bool:
        """
        Allow relations between objects in the same database group.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> Optional[bool]:
        """
        Only allow migrations on the primary database.
        """
        return db == 'default'


class MultiReplicaRouter:
    """
    Database router that load-balances read operations across multiple replicas.
    """

    def __init__(self):
        self.replicas = []

    def _get_replicas(self):
        """Get list of replica databases"""
        if not self.replicas:
            from django.conf import settings
            self.replicas = [
                db for db in settings.DATABASES.keys()
                if db.startswith('replica')
            ]
        return self.replicas

    def db_for_read(self, model, **hints) -> str:
        """
        Randomly select a replica for read operations.
        Falls back to default if no replicas configured.
        """
        replicas = self._get_replicas()
        if replicas:
            return random.choice(replicas)
        return 'default'

    def db_for_write(self, model, **hints) -> str:
        """
        Direct all write operations to primary database.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints) -> bool:
        """
        Allow relations between objects.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> Optional[bool]:
        """
        Only allow migrations on the primary database.
        """
        return db == 'default'


class ShardedRouter:
    """
    Database router for horizontal sharding based on organization_id.
    Use this for high-scale multi-tenant deployments.
    """

    def __init__(self):
        self.shard_count = 0
        self.shards = []

    def _get_shards(self):
        """Get list of shard databases"""
        if not self.shards:
            from django.conf import settings
            self.shards = [
                db for db in settings.DATABASES.keys()
                if db.startswith('shard')
            ]
            self.shard_count = len(self.shards)
        return self.shards

    def _get_shard_for_organization(self, organization_id: str) -> str:
        """Determine which shard an organization belongs to"""
        if not organization_id:
            return 'default'

        shards = self._get_shards()
        if not shards:
            return 'default'

        # Use hash of organization_id to determine shard
        shard_index = hash(organization_id) % self.shard_count
        return shards[shard_index]

    def db_for_read(self, model, **hints) -> str:
        """Route read to appropriate shard"""
        instance = hints.get('instance')
        if instance and hasattr(instance, 'organization_id'):
            return self._get_shard_for_organization(str(instance.organization_id))
        return 'default'

    def db_for_write(self, model, **hints) -> str:
        """Route write to appropriate shard"""
        instance = hints.get('instance')
        if instance and hasattr(instance, 'organization_id'):
            return self._get_shard_for_organization(str(instance.organization_id))
        return 'default'

    def allow_relation(self, obj1, obj2, **hints) -> bool:
        """
        Only allow relations between objects on the same shard.
        """
        db1 = self._get_shard_for_organization(
            getattr(obj1, 'organization_id', None)
        )
        db2 = self._get_shard_for_organization(
            getattr(obj2, 'organization_id', None)
        )
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> Optional[bool]:
        """
        Allow migrations on all shards.
        """
        return True
