# -*- coding: utf-8 -*-
import os, threading, time, warnings, serial, random
import mongomodels as models
import cloud_compost as cp

from flask.exthook import ExtDeprecationWarning
warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect, jsonify
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler


def add_measurement():
    models.measurements(m_type="sunlight_in", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="sunlight_out", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="soil_temp", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="soil_hum", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="air_temp_in", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="air_hum_in", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="air_temp_out", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
    models.measurements(m_type="air_hum_out", m_value=random.uniform(20.0, 85.0), compost=cp.compost_ID,
                        m_timestamp=datetime.now()).save()
