from django.db import models

class Trip(models.Model):
    trip_id = models.CharField(max_length=100, unique=True)
    trip_date = models.CharField(max_length=100, blank=True)
    vehicle_id = models.CharField(max_length=100, blank=True)
    driver_id = models.CharField(max_length=100, blank=True)
    planned_distance = models.FloatField(null=True, blank=True)
    advance_given = models.FloatField(null=True, blank=True)
    origin = models.CharField(max_length=200, blank=True)
    destination = models.CharField(max_length=200, blank=True)
    vehicle_type = models.CharField(max_length=100, blank=True)
    flags = models.CharField(max_length=200, blank=True)
    total_freight = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.trip_id

class TripClosure(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='closure')
    actual_distance = models.FloatField(null=True, blank=True)
    actual_delivery_date = models.CharField(max_length=100, blank=True)
    trip_delay_reason = models.CharField(max_length=300, blank=True)
    fuel_quantity = models.FloatField(null=True, blank=True)
    fuel_rate = models.FloatField(null=True, blank=True)
    fuel_cost = models.FloatField(null=True, blank=True)
    toll_charges = models.FloatField(null=True, blank=True)
    food_expense = models.FloatField(null=True, blank=True)
    lodging_expense = models.FloatField(null=True, blank=True)
    miscellaneous_expense = models.FloatField(null=True, blank=True)
    maintenance_cost = models.FloatField(null=True, blank=True)
    loading_charges = models.FloatField(null=True, blank=True)
    unloading_charges = models.FloatField(null=True, blank=True)
    penalty_fine = models.FloatField(null=True, blank=True)
    total_trip_expense = models.FloatField(null=True, blank=True)
    freight_amount = models.FloatField(null=True, blank=True)
    incentives = models.FloatField(null=True, blank=True)
    net_profit = models.FloatField(null=True, blank=True)
    payment_mode = models.CharField(max_length=100, blank=True)
    pod_status = models.CharField(max_length=50, blank=True)
    trip_status = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Closure {self.trip.trip_id}"
