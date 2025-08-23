from django.db import migrations

def seed_data(apps, schema_editor):
    Trip = apps.get_model('fleet', 'Trip')
    TripClosure = apps.get_model('fleet', 'TripClosure')
    if not Trip.objects.exists():
        Trip.objects.create(trip_id="T001", trip_date="2025-08-01", vehicle_id="V100", driver_id="D100", planned_distance=500, advance_given=2000, origin="CityA", destination="CityB", vehicle_type="Truck", flags="", total_freight=10000)
        Trip.objects.create(trip_id="T002", trip_date="2025-08-02", vehicle_id="V101", driver_id="D101", planned_distance=800, advance_given=3000, origin="CityB", destination="CityC", vehicle_type="Truck", flags="delay", total_freight=15000)
    if not TripClosure.objects.exists():
        TripClosure.objects.create(trip_id="T001", actual_distance=510, actual_delivery_date="2025-08-03", fuel_cost=1000, toll_charges=500, total_trip_expense=3000, freight_amount=10000, net_profit=7000, trip_status="Completed", pod_status="Yes")
        TripClosure.objects.create(trip_id="T002", actual_distance=820, actual_delivery_date="2025-08-04", fuel_cost=1500, toll_charges=600, total_trip_expense=4000, freight_amount=15000, net_profit=11000, trip_status="Pending Closure", pod_status="No")

class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_data),
    ]
