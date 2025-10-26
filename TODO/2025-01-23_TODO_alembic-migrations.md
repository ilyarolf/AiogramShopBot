# Alembic Database Migrations

**Date:** 2025-01-23
**Priority:** Medium
**Estimated Effort:** Medium (2-3 hours)

---

## Description
Implement Alembic for proper database schema migrations instead of manual SQL scripts. This provides version control for database changes, automatic migration generation, and safer schema updates.

## User Story
As a developer, I want automated database migrations so that schema changes are tracked, reversible, and can be safely applied across development, staging, and production environments.

## Current State
- **No migration system** - Schema changes require manual SQL scripts or DB drops
- **SQLAlchemy models** define schema, but changes don't auto-migrate
- **Manual migrations** in `migrations/` folder (SQL scripts)
- **Development workflow**: Drop DB and recreate (data loss)
- **Production risk**: Schema changes require careful manual SQL execution

## Problems with Current Approach
1. **Data Loss in Dev** - Dropping DB loses all test data
2. **No Version Tracking** - Can't see migration history
3. **No Rollback** - Can't undo migrations easily
4. **Manual Work** - Must write SQL for every schema change
5. **Production Risk** - Manual migrations error-prone
6. **Team Collaboration** - Hard to sync schema changes across team members

## Benefits of Alembic
- ✅ **Automatic migration generation** from SQLAlchemy model changes
- ✅ **Version control** for database schema
- ✅ **Rollback support** (upgrade/downgrade)
- ✅ **Production-safe** migrations
- ✅ **Team synchronization** - Git tracks migrations
- ✅ **Multi-environment** - Same migrations work everywhere

## Acceptance Criteria
- [ ] Alembic installed and configured
- [ ] `alembic.ini` configuration file created
- [ ] `alembic/` directory structure initialized
- [ ] Initial migration capturing current schema
- [ ] Automatic migration generation from model changes
- [ ] Migration commands documented in README
- [ ] Existing manual migrations converted to Alembic format (optional)
- [ ] CI/CD integration for automatic migration testing
- [ ] Team documentation for workflow

## Implementation Steps

### 1. Install Alembic
```bash
pip install alembic
pip freeze > requirements.txt
```

### 2. Initialize Alembic
```bash
alembic init alembic
```

This creates:
```
alembic/
├── versions/          # Migration files
├── env.py            # Alembic environment config
├── script.py.mako    # Template for new migrations
└── README
alembic.ini           # Main configuration
```

### 3. Configure `alembic.ini`
```ini
# Set SQLAlchemy URL
sqlalchemy.url = sqlite:///database.db

# For async SQLite (if needed)
# sqlalchemy.url = sqlite+aiosqlite:///database.db
```

### 4. Configure `alembic/env.py`
```python
# Import your models
from models.base import Base
from models.user import User
from models.item import Item
from models.order import Order
from models.shipping_address import ShippingAddress
# ... import all models

# Set target metadata
target_metadata = Base.metadata

# For autogenerate support
def run_migrations_online():
    # Your async SQLAlchemy engine setup
    # ...
```

### 5. Create Initial Migration
```bash
# Capture current schema
alembic revision --autogenerate -m "Initial schema"

# Review generated migration in alembic/versions/
# Edit if needed

# Apply migration
alembic upgrade head
```

### 6. Workflow for Future Changes

**When changing models:**
```bash
# 1. Edit model (e.g., add field to Item)
# models/item.py
class Item(Base):
    new_field = Column(String, nullable=True)

# 2. Generate migration
alembic revision --autogenerate -m "Add new_field to items"

# 3. Review migration file
# alembic/versions/xxx_add_new_field_to_items.py

# 4. Apply migration
alembic upgrade head

# 5. Commit migration file to git
git add alembic/versions/xxx_add_new_field_to_items.py
git commit -m "feat: add new_field to items table"
```

**Rollback if needed:**
```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Downgrade to beginning
alembic downgrade base
```

**Check current version:**
```bash
alembic current
alembic history
```

### 7. Convert Existing Manual Migrations

**Option A: Start Fresh**
- Create initial migration from current schema
- Archive old SQL scripts in `migrations/archive/`

**Option B: Create Historical Migrations**
- Create Alembic migrations matching old SQL scripts
- Maintain full migration history

## Configuration Example

### `alembic.ini`
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///database.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### `alembic/env.py` (async support)
```python
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import models
from models.base import Base
import models.user
import models.item
import models.order
import models.shipping_address
# ... all models

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
```

## Documentation Updates

### Update README.md
Add section:
```markdown
## Database Migrations

This project uses Alembic for database migrations.

### Initial Setup
\```bash
# Apply all migrations
alembic upgrade head
\```

### Development Workflow
When changing models:
\```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Review migration file in alembic/versions/

# Apply migration
alembic upgrade head
\```

### Common Commands
\```bash
alembic current              # Show current version
alembic history              # Show migration history
alembic upgrade head         # Apply all pending migrations
alembic downgrade -1         # Rollback last migration
alembic revision -m "msg"    # Create empty migration
\```
```

## Testing Strategy
1. Test migration generation with model changes
2. Test upgrade/downgrade cycles
3. Test on fresh database (no existing schema)
4. Test on existing database (with data)
5. Test concurrent migration attempts (team collaboration)

## CI/CD Integration
```yaml
# .github/workflows/test.yml
- name: Run database migrations
  run: alembic upgrade head

- name: Run tests
  run: pytest
```

## Known Issues & Solutions

**Issue: Alembic doesn't detect changes**
- Solution: Ensure all models imported in `env.py`
- Solution: Set `target_metadata = Base.metadata`

**Issue: Async SQLite conflicts**
- Solution: Use synchronous connection in migrations
- Alembic migrations run synchronously by default

**Issue: Manual SQL needed for data migrations**
- Solution: Use `op.execute()` in migration files
```python
def upgrade():
    # Schema change
    op.add_column('items', sa.Column('new_field', sa.String()))

    # Data migration
    op.execute("UPDATE items SET new_field='default' WHERE new_field IS NULL")
```

## Migration Examples

### Adding Column
```python
def upgrade():
    op.add_column('items', sa.Column('is_physical', sa.Boolean(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('items', 'is_physical')
```

### Creating Table
```python
def upgrade():
    op.create_table(
        'shipping_addresses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_address', sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    )

def downgrade():
    op.drop_table('shipping_addresses')
```

### Complex Data Migration
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new column
    op.add_column('orders', sa.Column('status_new', sa.String(50)))

    # Migrate data
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE orders
        SET status_new = CASE
            WHEN status = 0 THEN 'PENDING'
            WHEN status = 1 THEN 'PAID'
            ELSE 'UNKNOWN'
        END
    """))

    # Drop old column
    op.drop_column('orders', 'status')

    # Rename new column
    op.alter_column('orders', 'status_new', new_column_name='status')

def downgrade():
    # Reverse migration
    pass
```

## Dependencies
- `alembic>=1.13.0`
- Existing SQLAlchemy models
- Python 3.10+

## Related Issues
- Manual migrations in `migrations/` folder (to be archived)
- Production deployment requires DB migration strategy
- Team onboarding needs migration workflow docs

## References
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy Migrations Best Practices](https://alembic.sqlalchemy.org/en/latest/cookbook.html)

---

**Status:** Planned
**Notes:** Implement before production deployment. For now, manual SQL migrations or DB drops are acceptable in development.
