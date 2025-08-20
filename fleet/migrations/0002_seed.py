from django.db import migrations

def seed(apps, schema_editor):
    Trip = apps.get_model('fleet', 'Trip')
    TripClosure = apps.get_model('fleet', 'TripClosure')
    # Seed a few Trips
    trips = [
        dict(trip_id='T1001', trip_date='2025-07-10', vehicle_id='MH12AB1234', driver_id='D01', planned_distance=800, advance_given=5000, origin='Pune', destination='Bangalore', vehicle_type='Truck', flags='', total_freight=45000),
        dict(trip_id='T1002', trip_date='2025-07-12', vehicle_id='MH14XY9876', driver_id='D02', planned_distance=600, advance_given=3000, origin='Mumbai', destination='Surat', vehicle_type='Lorry', flags='Delay', total_freight=28000),
        dict(trip_id='T1003', trip_date='2025-07-15', vehicle_id='KA03MN4321', driver_id='D03', planned_distance=950, advance_given=7000, origin='Bangalore', destination='Hyderabad', vehicle_type='Trailer', flags='', total_freight=52000),
    ]
    for t in trips:
        Trip.objects.update_or_create(trip_id=t['trip_id'], defaults=t)

    # Seed closures
    closures = [
        dict(trip_id='T1001', actual_distance=820, actual_delivery_date='2025-07-12', fuel_quantity=220, fuel_rate=95, fuel_cost=20900, toll_charges=1500, food_expense=1200, lodging_expense=0, miscellaneous_expense=600, maintenance_cost=0, loading_charges=500, unloading_charges=600, penalty_fine=0, total_trip_expense=25300, freight_amount=45000, incentives=1000, net_profit=18700, payment_mode='Bank', pod_status='Yes', trip_status='Completed', remarks='On-time'),
        dict(trip_id='T1002', actual_distance=615, actual_delivery_date='2025-07-14', fuel_quantity=160, fuel_rate=95, fuel_cost=15200, toll_charges=800, food_expense=900, lodging_expense=0, miscellaneous_expense=300, maintenance_cost=0, loading_charges=400, unloading_charges=400, penalty_fine=0, total_trip_expense=18000, freight_amount=28000, incentives=0, net_profit=10000, payment_mode='Cash', pod_status='No', trip_status='Pending Closure', remarks='Delay due to traffic'),
    ]
    for c in closures:
        TripClosure.objects.update_or_create(trip_id=c['trip_id'], defaults=c)

def unseed(apps, schema_editor):
    Trip = apps.get_model('fleet', 'Trip')
    TripClosure = apps.get_model('fleet', 'TripClosure')
    Trip.objects.filter(trip_id__in=['T1001','T1002','T1003']).delete()
    TripClosure.objects.filter(trip_id__in=['T1001','T1002']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
