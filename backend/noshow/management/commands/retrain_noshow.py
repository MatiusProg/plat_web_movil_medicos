"""US-38: python manage.py retrain_noshow --all [--loop --every 1440].

Cron externo recomendado: ejecutar una vez al día. El modo --loop es opcional
para instalaciones sin cron. No arranca otro job de recordatorios ni scoring.
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from tenancy.context import platform_admin_context
from tenancy.models import Organization

from ... import retraining


class Command(BaseCommand):
    help = 'Reentrena sólo con desenlaces nuevos y promueve si mejora al vigente.'

    def add_arguments(self, parser):
        parser.add_argument('--organization', action='append', metavar='SLUG')
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--every', type=int, default=1440, help='Minutos entre ejecuciones')
        parser.add_argument('--min-new', type=int, default=retraining.MIN_NEW_OUTCOMES)

    def handle(self, *args, **options):
        slugs = options['organization']
        if not slugs and not options['all']:
            raise CommandError('Indicá --organization SLUG o --all.')
        if options['every'] < 1 or options['min_new'] < 1:
            raise CommandError('--every y --min-new deben ser positivos.')
        if slugs:
            with platform_admin_context():
                existing = set(Organization.objects.filter(slug__in=slugs).values_list('slug', flat=True))
            missing = set(slugs) - existing
            if missing:
                raise CommandError('Organizaciones desconocidas: ' + ', '.join(sorted(missing)))

        def run():
            for slug, result in retraining.run_due(slugs=slugs, min_new=options['min_new']):
                self.stdout.write(f'{slug}: {result.action} — {result.message}')

        if not options['loop']:
            run()
            return
        while True:
            try:
                run()
            finally:
                close_old_connections()
            time.sleep(options['every'] * 60)
