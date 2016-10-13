# -*- coding: utf-8 -*-
import os, threading, time, warnings, serial, random
import cloud_compost as cc

from flask.exthook import ExtDeprecationWarning
warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect, jsonify
from flask_mongoengine import MongoEngine
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

db = MongoEngine(cc.app)


# ##################    MODELS     ###################################
class compost_devices(db.Document):
    name = db.StringField(max_length=50)
    country = db.StringField(max_length=50)
    region = db.StringField(max_length=50)
    area = db.StringField(max_length=50)
    ip = db.StringField(max_length=100)


class Log(db.Document):
    l_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    action = db.StringField()
    compost = db.ReferenceField(compost_devices, required=True)
    meta = {'max_documents': 100}


class Errors(db.Document):
    e_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    error = db.StringField()
    compost = db.ReferenceField(compost_devices, required=True)
    meta = {'max_documents': 100}


class compost_Settings(db.Document):
    daily_soil_backward_time = db.StringField(default='14:00pm')
    daily_steering_time = db.StringField(default='06:00am')
    steering_duration = db.StringField(max_length=10, default='30000')
    motor_F_duration = db.StringField(max_length=10, default=60)
    motor_B_duration = db.StringField(max_length=10, default=60)
    motor_R_duration = db.StringField(max_length=10, default=60)
    motor_L_duration = db.StringField(max_length=10, default=60)
    vent_duration = db.StringField(max_length=10, default=300)
    lowest_soil_humidity = db.StringField(max_length=10, default='55')
    highest_soil_humidity = db.StringField(max_length=10, default='65')
    lowest_soil_temperature = db.StringField(max_length=10, default='50')
    usb_port = db.StringField(default='/dev/cu.usbmodem1411')
    sleep_time_for_motors = db.StringField(max_length=10, default='30')


class compost_Flags(db.Document):
    Motor_F = db.BooleanField(default=False)
    Motor_B = db.BooleanField(default=False)
    Motor_R = db.BooleanField(default=False)
    Motor_L = db.BooleanField(default=False)
    Fan = db.BooleanField(default=False)
    Vent = db.BooleanField(default=False)
    Door_1 = db.BooleanField(default=False)
    # Door_2 = db.BooleanField(default=False)
    Emergency_Stop = db.BooleanField(default=False)
    compost = db.ReferenceField(compost_devices, required=True)

    def __str__(self):
        return self.name


class measurements(db.Document):
    m_type = db.StringField(max_length=100)
    m_value = db.FloatField(max_length=6)
    compost = db.ReferenceField(compost_devices, required=True)
    m_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    meta = {'max_documents': 5000}

    def __str__(self):
        return self.name
