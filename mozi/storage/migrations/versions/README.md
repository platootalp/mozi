# Migration versions

This directory contains individual migration files.

To add a new migration:

1. Create a new file named `vXXX_description.py` where XXX is the version number
2. Define a migration function that takes a sqlite3.Connection
3. Register it using the `@register_migration(version)` decorator
4. Import it in `manager.py`
