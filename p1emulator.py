import serial
import time
import datetime
import random


SERIAL_PORT = "COM1"
BAUDRATE = 115200
INTERVAL = 1


def crc16_ansi_ibm(data: bytes) -> int:
    polynomial = 0xA001
    crc = 0x0000

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1

    return crc & 0xFFFF

def dsmr_timestamp():
    now = datetime.datetime.now()

    dst = now.astimezone().dst()
    suffix = "S" if dst and dst.total_seconds() != 0 else "W"

    return now.strftime("%y%m%d%H%M%S") + suffix

class DSMRModel:
    def __init__(self):
        self.energy_t1 = 9159.772
        self.energy_t2 = 6069.669
        self.energy_return_t1 = 0.0
        self.energy_return_t2 = 0.0

        self.power = 0.5  # kW initial
        self.last_update = time.monotonic()

    def current_tariff(self):
        hour = datetime.datetime.now().hour
        return 1 if hour < 7 or hour >= 23 else 2

    def update(self):
        now = time.monotonic()
        dt = now - self.last_update
        self.last_update = now

        if self.power < 1.9:
            # Smooth random load
            target = random.uniform(0.2, 1.8)
            self.power = 0.9 * self.power + 0.1 * target

        delta_kwh = self.power * dt / 3600.0
        tariff = self.current_tariff()

        if self.power >= 0:
            if tariff == 1:
                self.energy_t1 += delta_kwh
            else:
                self.energy_t2 += delta_kwh
        else:
            if tariff == 1:
                self.energy_return_t1 += abs(delta_kwh)
            else:
                self.energy_return_t2 += abs(delta_kwh)

        return tariff

    def voltages(self):
        return [230 + random.uniform(-2, 2) for _ in range(3)]

    def currents(self, voltages):
        total_power_w = self.power * 1000
        per_phase_w = total_power_w / 3

        currents = []
        for v in voltages:
            if v <= 0:
                currents.append(0)
            else:
                currents.append(per_phase_w / v)
        return currents
    
def f_energy(v):
    return f"{v:09.3f}"

def f_power(v):
    return f"{abs(v):06.3f}"

def f_voltage(v):
    return f"{v:05.1f}"

def f_current(i):
    return f"{abs(i):03.0f}"

def input_thread(model):
    while True:
        cmd = input()
        try:
            value = float(cmd)
            model.power = value
            print(f"Base load set to {value} kW")
        except ValueError:
            print("Enter a numeric value")

model = DSMRModel()

def build_telegram(model: DSMRModel):
    tariff = model.update()
    timestamp = dsmr_timestamp()
    voltages = model.voltages()
    currents = model.currents(voltages)

    body = (
        "/SIMULATOR\r\n"
        f"0-0:1.0.0({timestamp})\r\n"
        f"0-0:96.14.0(000{tariff})\r\n"
        f"1-0:1.8.1({f_energy(model.energy_t1)}kWh)\r\n"
        f"1-0:1.8.2({f_energy(model.energy_t2)}kWh)\r\n"
        f"1-0:2.8.1({f_energy(model.energy_return_t1)}kWh)\r\n"
        f"1-0:2.8.2({f_energy(model.energy_return_t2)}kWh)\r\n"
        f"1-0:1.7.0({f_power(model.power)}kW)\r\n"
        f"1-0:2.7.0(00.000kW)\r\n"
        f"1-0:32.7.0({f_voltage(voltages[0])}V)\r\n"
        f"1-0:52.7.0({f_voltage(voltages[1])}V)\r\n"
        f"1-0:72.7.0({f_voltage(voltages[2])}V)\r\n"
        f"1-0:31.7.0({f_current(currents[0])}A)\r\n"
        f"1-0:51.7.0({f_current(currents[1])}A)\r\n"
        f"1-0:71.7.0({f_current(currents[2])}A)\r\n"
    )

    crc_data = (body + "!").encode("ascii")
    crc = crc16_ansi_ibm(crc_data)

    return crc_data + f"{crc:04X}\r\n".encode("ascii")



def main():
    
    with serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
    ) as ser:

        next_send = time.monotonic()

        while True:
            telegram = build_telegram(model)
            ser.write(telegram)
            ser.flush()
            print("Sent telegram")
            time.sleep(0.05)

            next_send += INTERVAL
            sleep = next_send - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)


if __name__ == "__main__":
    main()
