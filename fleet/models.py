from django.db import models

class Trip(models.Model):
    trip_id = models.CharField(max_length=100)
    trip_date = models.CharField(max_length=50, blank=True)
    vehicle_id = models.CharField(max_length=100, blank=True)
    driver_id = models.CharField(max_length=100, blank=True)
    planned_distance = models.FloatField(default=0)
    advance_given = models.FloatField(default=0)
    origin = models.CharField(max_length=100, blank=True)
    destination = models.CharField(max_length=100, blank=True)
    vehicle_type = models.CharField(max_length=100, blank=True)
    flags = models.TextField(blank=True)
    total_freight = models.FloatField(default=0)

    def __str__(self):
        return self.trip_id

class TripClosure(models.Model):
    trip_id = models.CharField(primary_key=True, max_length=100)
    actual_distance = models.FloatField(default=0)
    actual_delivery_date = models.CharField(max_length=50, blank=True)
    trip_delay_reason = models.TextField(blank=True)
    fuel_quantity = models.FloatField(default=0)
    fuel_rate = models.FloatField(default=0)
    fuel_cost = models.FloatField(default=0)
    toll_charges = models.FloatField(default=0)
    food_expense = models.FloatField(default=0)
    lodging_expense = models.FloatField(default=0)
    miscellaneous_expense = models.FloatField(default=0)
    maintenance_cost = models.FloatField(default=0)
    loading_charges = models.FloatField(default=0)
    unloading_charges = models.FloatField(default=0)
    penalty_fine = models.FloatField(default=0)
    total_trip_expense = models.FloatField(default=0)
    freight_amount = models.FloatField(default=0)
    incentives = models.FloatField(default=0)
    net_profit = models.FloatField(default=0)
    payment_mode = models.CharField(max_length=50, blank=True)
    pod_status = models.CharField(max_length=50, blank=True)
    trip_status = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.trip_id
