import json
#import math
#import time
import paho.mqtt.client as mqtt
from river import anomaly
from river import preprocessing

# --------------------------
# Model
# --------------------------

model = preprocessing.StandardScaler() | anomaly.HalfSpaceTrees(
    n_trees=30,
    height=6,
    window_size=300,
    seed=42
)

THRESHOLD = 0.98
WARMUP = 300
sample_count = 0
prev_power = None

# --------------------------
# Shared State
# --------------------------

state = {
    "power": None,
    "v1": None,
    "v2": None,
    "v3": None,
}


# --------------------------
# MQTT Callback
# --------------------------

def on_message(client, userdata, msg):
    global sample_count, prev_power

    topic = msg.topic
    data = json.loads(msg.payload)

    # Update state depending on topic
    if topic == "domo/1/state":
        state["power"] = float(data["usage_current"]) / 1000.0

    elif topic == "domo/2/state":
        state["v1"] = float(data["voltage"])

    elif topic == "domo/3/state":
        state["v2"] = float(data["voltage"])

    elif topic == "domo/4/state":
        state["v3"] = float(data["voltage"])

    # Only proceed if all values exist
    if None in state.values():
        return

    power = state["power"]

    # Derived feature: delta
    if prev_power is None:
        delta = 0.0
    else:
        delta = power - prev_power

    prev_power = power

    # Time encoding
    #now = time.localtime()
    #hour = now.tm_hour + now.tm_min / 60.0 + now.tm_sec / 3600.0

    #hour_sin = math.sin(2 * math.pi * hour / 24)
    #hour_cos = math.cos(2 * math.pi * hour / 24)

    # Feature vector
    x = {
        "power": power,
        "delta": delta,
        "v1": state["v1"],
        "v2": state["v2"],
        "v3": state["v3"],
        #"hour_sin": hour_sin,
        #"hour_cos": hour_cos,
    }

    score = model.score_one(x)
    sample_count += 1

    if sample_count > WARMUP:

        print(f"Score: {score:.4f}")

        if score > THRESHOLD:
            print("ANOMALY DETECTED", x)

    else:
        
        print(f"Warmup {sample_count}/{WARMUP}")
        print(x)
        
    model.learn_one(x)
    state["power"] = None
    state["v1"] = None
    state["v2"] = None
    state["v3"] = None
# --------------------------
# MQTT Setup
# --------------------------

client = mqtt.Client()
client.connect("localhost", 1883)

client.subscribe("domo/1/state")
client.subscribe("domo/2/state")
client.subscribe("domo/3/state")
client.subscribe("domo/4/state")

client.on_message = on_message
client.loop_forever()