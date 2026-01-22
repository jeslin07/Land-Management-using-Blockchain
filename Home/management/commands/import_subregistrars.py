import csv
from django.core.management.base import BaseCommand
from Home.models import SubRegistrarOffice

class Command(BaseCommand):
    help = 'Import districts and localities from CSV'

    def handle(self, *args, **kwargs):
        with open('Home/subregistrars.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            district_map = {
                'trivandrum': 'thiruvananthapuram',
                'thiruvananthapuram': 'thiruvananthapuram',
                'kollam': 'kollam',
                'pathanamthitta': 'pathanamthitta',
                'alappuzha': 'alappuzha',
                'kottayam': 'kottayam',
                'idukki': 'idukki',
                'ernakulam': 'ernakulam',
                'thrissur': 'thrissur',
                'palakkad': 'palakkad',
                'malappuram': 'malappuram',
                'kozhikode': 'kozhikode',
                'wayanad': 'wayanad',
                'kannur': 'kannur',
                'kasaragod': 'kasaragod',
            }

            for row in reader:
                district_key = row['District in which Office located'].strip().lower()
                district = district_map.get(district_key, district_key)

                # Split office name and locality from the column
                office_full = row['Name& Location of Office'].strip()
                if ',' in office_full:
                    name, locality = [part.strip() for part in office_full.split(',', 1)]
                else:
                    name = office_full
                    locality = ''  # blank if no locality info

                SubRegistrarOffice.objects.create(
                    name=name,
                    district=district,
                    locality=locality
                )

        self.stdout.write(self.style.SUCCESS('CSV imported successfully!'))
