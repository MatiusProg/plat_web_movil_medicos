"""US-03 — La tabla de tokens de restablecimiento, con su aislamiento.

La política RLS va en **esta misma migración** y no en una aparte, a propósito:
las convenciones (§5) exigen que toda tabla con ``organization_id`` tenga
``ENABLE`` y ``FORCE ROW LEVEL SECURITY`` y su clave foránea compuesta, y si
eso viviera en otra migración existiría una ventana —entre una y otra— en la
que la tabla está creada y desprotegida. Con el RLS acá, la tabla nunca existe
sin él.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

# Lo mismo que hace `tenancy/0002_rls_policies` con las tablas del Sprint 0.
# Sin `FORCE`, el dueño del esquema —que es `app_user`, el propio usuario de la
# aplicación— quedaría exento de sus propias reglas.
AISLAMIENTO = """
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens FORCE  ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON password_reset_tokens
    USING (organization_id = app_current_tenant())
    WITH CHECK (organization_id = app_current_tenant());

-- Un token no puede apuntar al usuario de otra organización.
--
-- Django crea una clave foránea simple contra users(id). Se la reemplaza por
-- la compuesta (user_id, organization_id), que es la que impide que una fila
-- de un inquilino referencie a un usuario de otro. Es el mismo patrón que
-- `fk_user_role_role_same_org`, y lo que lo hace posible es la restricción
-- `uq_user_id_org` de la tabla users.
DO $do$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'password_reset_tokens'::regclass AND contype = 'f'
           AND confrelid = 'users'::regclass
    LOOP
        EXECUTE format('ALTER TABLE password_reset_tokens DROP CONSTRAINT %I', c);
    END LOOP;
END
$do$;

ALTER TABLE password_reset_tokens ADD CONSTRAINT fk_password_reset_user_same_org
    FOREIGN KEY (user_id, organization_id)
    REFERENCES users (id, organization_id) ON DELETE CASCADE;
"""

# Al revertir, la operación siguiente borra la tabla entera; alcanza con soltar
# lo que se agregó a mano para que el DROP no encuentre dependencias.
SIN_AISLAMIENTO = """
ALTER TABLE password_reset_tokens
    DROP CONSTRAINT IF EXISTS fk_password_reset_user_same_org;
DROP POLICY IF EXISTS tenant_isolation ON password_reset_tokens;
ALTER TABLE password_reset_tokens NO FORCE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_seed_permissions_sprint_1'),
        ('tenancy', '0003_seed_catalog'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to='tenancy.organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'token de restablecimiento',
                'verbose_name_plural': 'tokens de restablecimiento',
                'db_table': 'password_reset_tokens',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', '-created_at'], name='ix_password_reset_user')],
            },
        ),
        migrations.RunSQL(AISLAMIENTO, SIN_AISLAMIENTO),
    ]
