"""Onward Logistics order system: one container serving the UI and the order logic."""

import json                                                # Parse the ECS metadata response
import os                                                  # Read environment variables
import socket                                              # Get the container hostname
import time                                                # Timing for the CPU burner
import urllib.request                                      # Call the local ECS metadata endpoint
from datetime import datetime, timezone                    # Timestamps for orders
from itertools import count                                # Simple order ID sequence

from flask import Flask, jsonify, render_template, request  # Web framework pieces

import settings                                            # Release settings (name, lab, demo switch)

app = Flask(__name__)                                      # Create the web application

APP_VERSION = os.getenv("APP_VERSION", "dev")              # Git SHA baked in at build time
_order_ids = count(1001)                                   # Order numbers start at 1001
ORDERS = []                                                # In-memory demo orders (per task)


def task_location():
    """Return (task id, availability zone) from ECS metadata, or local values off ECS."""
    uri = os.getenv("ECS_CONTAINER_METADATA_URI_V4")       # Set by Fargate inside every task
    if not uri:                                            # Running locally (docker run)
        return socket.gethostname(), "local"               # Hostname and a placeholder AZ
    try:                                                   # Metadata is link-local, no internet needed
        with urllib.request.urlopen(f"{uri}/task", timeout=1) as resp:  # Ask ECS about this task
            meta = json.load(resp)                         # Parse JSON
        task_id = meta.get("TaskARN", "").rsplit("/", 1)[-1][:12]  # Short task ID
        return task_id, meta.get("AvailabilityZone", "unknown")    # ID and AZ
    except Exception:                                      # Never let metadata break the page
        return socket.gethostname(), "unknown"             # Fallback values


TASK_ID, AZ = task_location()                              # Looked up once at start-up


@app.get("/")
def index():
    """Home page: student name, lab name, version and which task/AZ answered."""
    return render_template(                                # Render templates/index.html
        "index.html",                                      # Template file
        student=settings.STUDENT_NAME,                     # Full name
        lab=settings.LAB_NAME,                             # Lab name
        version=APP_VERSION,                               # Release version (git SHA)
        note=settings.RELEASE_NOTE,                        # Release note
        task_id=TASK_ID,                                   # Task that served the request
        az=AZ,                                             # AZ of that task
        orders=list(reversed(ORDERS[-10:])),               # Latest 10 orders, newest first
    )


@app.post("/orders")
def create_order():
    """Create a demo order from a form post or JSON body."""
    data = request.get_json(silent=True) or request.form    # Accept JSON or HTML form
    item = (data.get("item") or "").strip()[:60]           # Clean, length-limited item name
    qty = int(data.get("quantity") or 1)                   # Quantity, default 1
    if not item or not 1 <= qty <= 1000:                   # Basic validation
        return jsonify(error="item required, quantity 1-1000"), 400  # Bad request
    order = {                                              # Build the order record
        "id": next(_order_ids),                            # Next order number
        "item": item,                                      # What was ordered
        "quantity": qty,                                   # How many
        "created": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),  # When
        "task": TASK_ID,                                   # Which task took it
    }
    ORDERS.append(order)                                   # Store in memory
    if request.is_json:                                    # API caller
        return jsonify(order), 201                         # Return JSON
    return index()                                         # Browser: show the page again


@app.get("/health")
def health():
    """ALB health check. Returns 500 only when the bad-release demo switch is on."""
    if settings.FORCE_UNHEALTHY:                           # Deliberately broken release
        return "unhealthy", 500                            # ALB marks the task unhealthy
    return "ok", 200                                       # Healthy


@app.get("/version")
def version():
    """Machine-readable version, used by the zero-downtime curl loop."""
    return jsonify(version=APP_VERSION, task=TASK_ID, az=AZ)  # Version + location


@app.get("/cpu")
def burn_cpu():
    """Burn CPU for N seconds (max 10) to demo auto scaling."""
    seconds = min(float(request.args.get("seconds", 2)), 10.0)  # Cap the burn time
    end = time.time() + seconds                            # Stop time
    n = 0                                                  # Busy-work counter
    while time.time() < end:                               # Spin until time is up
        n += 1                                             # Pure CPU work
    return jsonify(burned_seconds=seconds, iterations=n, task=TASK_ID)  # Report


if __name__ == "__main__":                                 # Local run without gunicorn
    app.run(host="0.0.0.0", port=8080)                     # Same port as the container
