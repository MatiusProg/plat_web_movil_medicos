"""Característica general 6 — Copias automáticas.

``backup_records.trigger`` distingue las manuales de las automáticas, y
``backup_files`` guarda el archivo cifrado de las automáticas. Ver
``backups/automatic.py`` y ``backups/vault.py``.

``backup_files`` lleva RLS por inquilino como ``backup_records``: el contenido
está cifrado, pero que una organización ni siquiera vea que existen las copias
de otra no depende de eso.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models


RLS = """
    ALTER TABLE backup_files ENABLE ROW LEVEL SECURITY;
    ALTER TABLE backup_files FORCE  ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON backup_files
        USING (organization_id = app_current_tenant())
        WITH CHECK (organization_id = app_current_tenant());
"""

NO_RLS = """
    DROP POLICY IF EXISTS tenant_isolation ON backup_files;
    ALTER TABLE backup_files NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE backup_files DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0002_rls_and_permissions'),
        ('tenancy', '0006_backup_retention'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuprecord',
            name='trigger',
            field=models.CharField(choices=[('manual', 'Manual'), ('automatic', 'Automática')], default='manual', max_length=10),
        ),
        migrations.CreateModel(
            name='StoredBackup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stored_backups', to='tenancy.organization')),
                ('record', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stored', to='backups.backuprecord')),
            ],
            options={
                'verbose_name': 'copia automática guardada',
                'verbose_name_plural': 'copias automáticas guardadas',
                'db_table': 'backup_files',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['organization', '-created_at'], name='ix_backup_files_org')],
            },
        ),
        migrations.RunSQL(RLS, NO_RLS),
    ]
