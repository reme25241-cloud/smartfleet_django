from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trip_id', models.CharField(max_length=100)),
                ('trip_date', models.CharField(blank=True, max_length=50)),
                ('vehicle_id', models.CharField(blank=True, max_length=100)),
                ('driver_id', models.CharField(blank=True, max_length=100)),
                ('planned_distance', models.FloatField(default=0)),
                ('advance_given', models.FloatField(default=0)),
                ('origin', models.CharField(blank=True, max_length=100)),
                ('destination', models.CharField(blank=True, max_length=100)),
                ('vehicle_type', models.CharField(blank=True, max_length=100)),
                ('flags', models.TextField(blank=True)),
                ('total_freight', models.FloatField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='TripClosure',
            fields=[
                ('trip_id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('actual_distance', models.FloatField(default=0)),
                ('actual_delivery_date', models.CharField(blank=True, max_length=50)),
                ('trip_delay_reason', models.TextField(blank=True)),
                ('fuel_quantity', models.FloatField(default=0)),
                ('fuel_rate', models.FloatField(default=0)),
                ('fuel_cost', models.FloatField(default=0)),
                ('toll_charges', models.FloatField(default=0)),
                ('food_expense', models.FloatField(default=0)),
                ('lodging_expense', models.FloatField(default=0)),
                ('miscellaneous_expense', models.FloatField(default=0)),
                ('maintenance_cost', models.FloatField(default=0)),
                ('loading_charges', models.FloatField(default=0)),
                ('unloading_charges', models.FloatField(default=0)),
                ('penalty_fine', models.FloatField(default=0)),
                ('total_trip_expense', models.FloatField(default=0)),
                ('freight_amount', models.FloatField(default=0)),
                ('incentives', models.FloatField(default=0)),
                ('net_profit', models.FloatField(default=0)),
                ('payment_mode', models.CharField(blank=True, max_length=50)),
                ('pod_status', models.CharField(blank=True, max_length=50)),
                ('trip_status', models.CharField(blank=True, max_length=50)),
                ('remarks', models.TextField(blank=True)),
            ],
        ),
    ]
