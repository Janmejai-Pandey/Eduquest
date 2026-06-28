"""
ece_data.py
Electronics and Communication Engineering job role profiles.
"""

job_skill_profiles = {
    "VLSI Design Engineer": {
        "skills": [
            "verilog", "vhdl", "systemverilog", "uvm", "ovm",
            "rtl design", "synthesis", "place and route", "timing analysis",
            "static timing analysis", "sta", "asic design", "fpga",
            "xilinx", "altera", "intel", "cadence", "synopsys",
            "design compiler", "primetime", "innovus", "spice",
            "circuit design", "digital design", "analog design",
            "low power design", "clock domain crossing", "tcl",
            "python", "perl", "linux", "git", "version control"
        ],
        "weights": {
            "verilog": 5, "vhdl": 4, "systemverilog": 5, "rtl design": 5,
            "synthesis": 4, "timing analysis": 4, "asic design": 4,
            "fpga": 4, "digital design": 5, "linux": 3
        }
    },
    "Embedded Systems Engineer": {
        "skills": [
            "c", "c++", "rust", "python", "assembly", "rtos", "freertos",
            "bare metal", "microcontrollers", "arm", "cortex", "avr",
            "pic", "stm32", "esp32", "arduino", "raspberry pi", "fpga",
            "verilog", "iot", "sensors", "actuators", "uart", "spi",
            "i2c", "can", "modbus", "ethernet", "wifi", "bluetooth",
            "zigbee", "lora", "pcb design", "altium", "kicad",
            "oscilloscope", "logic analyzer", "debugger", "jtag",
            "git", "agile", "unit testing"
        ],
        "weights": {
            "c": 5, "c++": 4, "rtos": 5, "microcontrollers": 5,
            "arm": 4, "stm32": 4, "uart": 3, "spi": 3, "i2c": 3,
            "pcb design": 3, "git": 2
        }
    },
    "Communication Engineer": {
        "skills": [
            "digital signal processing", "dsp", "communication systems",
            "wireless communication", "5g", "4g", "lte", "ofdm", "mimo",
            "antenna design", "rf engineering", "modulation", "demodulation",
            "channel coding", "matlab", "simulink", "python", "c++",
            "labview", "spectrum analyzer", "vector network analyzer",
            "oscilloscope", "tcp/ip", "networking", "protocols",
            "satellite communication", "fiber optics", "microwave",
            "verilog", "fpga", "git", "linux"
        ],
        "weights": {
            "digital signal processing": 5, "communication systems": 5,
            "wireless communication": 4, "5g": 4, "matlab": 4,
            "antenna design": 4, "modulation": 4, "rf engineering": 4
        }
    },
    "RF Engineer": {
        "skills": [
            "rf design", "microwave engineering", "antenna design",
            "transmission lines", "smith chart", "s-parameters",
            "matlab", "ads", "hfss", "cst", "ansys", "keysight",
            "spectrum analyzer", "vector network analyzer", "signal generator",
            "oscilloscope", "amplifier design", "mixer design",
            "filter design", "pll design", "vco design", "modulation",
            "wireless communication", "5g", "wifi", "bluetooth",
            "satellite communication", "pcb design", "altium", "linux",
            "python", "git"
        ],
        "weights": {
            "rf design": 5, "antenna design": 5, "microwave engineering": 4,
            "matlab": 4, "ads": 4, "hfss": 4,
            "wireless communication": 4, "pcb design": 3
        }
    },
    "Hardware Design Engineer": {
        "skills": [
            "circuit design", "analog design", "digital design",
            "pcb design", "altium", "kicad", "eagle", "orcad",
            "schematic capture", "layout", "signal integrity",
            "power integrity", "emi/emc", "spice", "ltspice", "cadence",
            "mentor graphics", "microcontrollers", "fpga", "verilog",
            "vhdl", "soldering", "prototyping", "testing", "debugging",
            "oscilloscope", "logic analyzer", "multimeter", "spectrum analyzer",
            "manufacturing", "design for manufacturing", "git"
        ],
        "weights": {
            "circuit design": 5, "pcb design": 5, "altium": 4,
            "signal integrity": 4, "schematic capture": 4, "spice": 4,
            "microcontrollers": 4, "prototyping": 4
        }
    },
    "IoT Engineer": {
        "skills": [
            "c", "c++", "python", "embedded systems", "microcontrollers",
            "arduino", "raspberry pi", "esp32", "stm32", "rtos",
            "iot protocols", "mqtt", "coap", "http", "websocket",
            "lorawan", "zigbee", "bluetooth", "wifi", "5g", "nb-iot",
            "aws iot", "azure iot", "google cloud iot", "edge computing",
            "sensor integration", "actuator control", "pcb design",
            "soldering", "data analytics", "machine learning",
            "security", "encryption", "linux", "git", "agile"
        ],
        "weights": {
            "c": 4, "c++": 4, "python": 4, "embedded systems": 5,
            "iot protocols": 5, "mqtt": 4, "aws iot": 4,
            "microcontrollers": 4, "sensor integration": 4, "git": 3
        }
    },
    "Power Electronics Engineer": {
        "skills": [
            "power electronics", "circuit design", "smps", "dc-dc converter",
            "ac-dc converter", "inverter", "rectifier", "pwm",
            "motor control", "bldc", "induction motor", "stepper motor",
            "matlab", "simulink", "pspice", "ltspice", "psim",
            "magnetics", "transformer design", "inductor design",
            "thermal management", "battery management", "ev",
            "renewable energy", "solar inverters", "pcb design",
            "altium", "embedded systems", "microcontrollers", "stm32",
            "control systems", "pid control", "git"
        ],
        "weights": {
            "power electronics": 5, "circuit design": 4, "smps": 4,
            "matlab": 4, "motor control": 4, "pwm": 4,
            "pcb design": 3, "control systems": 4
        }
    }
}