from django.core.management.base import BaseCommand
from django.utils import timezone
from home.models import Bus

class Command(BaseCommand):
    help = 'Updates bus status to under_maintenance if arrival date has passed'

    def handle(self, *args, **options):
        buses = Bus.objects.all()
        updated_count = 0

        for bus in buses:
            if bus.should_be_under_maintenance() and bus.status != 'under_maintenance':
                bus.update_status()
                bus.save()
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} buses to under_maintenance status'
            )
        )
