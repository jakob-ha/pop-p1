import json
import math
import paho.mqtt.client as mqtt
from river import stats

# --- Running variance for envelope ---

baseline = None
ALPHA = 0.02            # adaptation speed
Z_THRESHOLD = 3         # envelope width
MIN_SAMPLES = 50
loops = 0
anomaly_combo_counter = 0
alive_counter = 0

variance = stats.EWVar(fading_factor=ALPHA)

# ------------------------
# VOLTAGE: Rolling stats
# ------------------------

v1_mean = stats.Mean()
v1_var  = stats.Var()

v2_mean = stats.Mean()
v2_var  = stats.Var()

v3_mean = stats.Mean()
v3_var  = stats.Var()

VOLTAGE_Z_THRESHOLD = 4  # 4σ is conservative


def check_voltage(name, value, mean_obj, var_obj):
    mean_obj.update(value)
    var_obj.update(value)

    if var_obj.n > 30:  # wait for stabilization
        std = math.sqrt(var_obj.get())
        z = abs(value - mean_obj.get()) / std if std > 0 else 0

        if z > VOLTAGE_Z_THRESHOLD:
            print(f"VOLTAGE ANOMALY {name}: {value:.2f}V  z={z:.2f}")

state = {
    "power": None,
    "v1": None,
    "v2": None,
    "v3": None,
}

def on_message(client, userdata, msg):
    global baseline
    global loops
    global anomaly_combo_counter
    global alive_counter
    topic = msg.topic
    data = json.loads(msg.payload)

    if topic == "domo/1/state":
        state["power"] = float(data["usage_current"])

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
    v1 = state["v1"]
    v2 = state["v2"]
    v3 = state["v3"]

    # ---- POWER ----

     # Initialize baseline
    if baseline is None:
        baseline = power

    # Update baseline slowly
    baseline = ALPHA * power + (1 - ALPHA) * baseline

    # Update variance
    variance.update(power)
    
    state["power"] = None
    state["v1"] = None
    state["v2"] = None
    state["v3"] = None
    
    loops += 1


    if loops < MIN_SAMPLES:
        print(f"Warmup {loops}/{MIN_SAMPLES}")
        return

    std = math.sqrt(variance.get())

    if std == 0:
        return

    z = abs(power - baseline) / std

    if z > Z_THRESHOLD:
        print("POWER ANOMALY")
        anomaly_combo_counter += 1
        print(f"Power={power:.1f}  baseline={baseline:.1f}  z={z:.2f}")
    else:
        anomaly_combo_counter = 0
        
    if anomaly_combo_counter > 10:
        print("IT'S REAL")
    
    imbalance = max(v1, v2, v3) - min(v1, v2, v3)

    if imbalance > 5:
        print("PHASE IMBALANCE DETECTED")
        print(f"V1:{v1} V2:{v2} V3:{v3}")
    
    # ---- VOLTAGES ----
    check_voltage("L1", v1, v1_mean, v1_var)
    check_voltage("L2", v2, v2_mean, v2_var)
    check_voltage("L3", v3, v3_mean, v3_var)
    
    
    alive_counter += 1
    
    if alive_counter % 10 == 0:
        print(f"This runs every 10 messages: Power={power:.1f}  baseline={baseline:.1f}  z={z:.2f} V1:{v1} V2:{v2} V3:{v3}")
    

    
    


client = mqtt.Client()
client.connect("localhost", 1883)
client.subscribe("domo/1/state")
client.subscribe("domo/2/state")
client.subscribe("domo/3/state")
client.subscribe("domo/4/state")
client.on_message = on_message

client.loop_forever()