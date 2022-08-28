import matplotlib.pyplot as plt
import numpy as np
import json, os

CORA_PATH = "cora_stats/"
CITESEER_PATH = "citeseer_stats/"

cora_accs = []
cora_rates = []

for fle in os.listdir(CORA_PATH):
    path_string = CORA_PATH + fle
    with open(path_string, "r") as f:
        data = json.load(f)

    cora_accs.append(data['acc_mean'])
    cora_rates.append(data['damage_rate'])

assert len(cora_accs) == len(cora_rates)
cora_new_data = [[cora_accs[i], cora_rates[i]] for i in range(len(cora_accs))]
cora_new_data.sort(key=lambda r : r[1])
cora_accs = [rec[0] for rec in cora_new_data]
cora_rates = [rec[1] for rec in cora_new_data]

cs_accs = []
cs_rates = []

for fle in os.listdir(CITESEER_PATH):
    path_string = CITESEER_PATH + fle
    with open(path_string, "r") as f:
        data = json.load(f)

    cs_accs.append(data['acc_mean'])
    cs_rates.append(data['damage_rate'])

assert len(cs_accs) == len(cs_rates)
cs_new_data = [[cs_accs[i], cs_rates[i]] for i in range(len(cs_accs))]
cs_new_data.sort(key=lambda r : r[1])
cs_accs = [rec[0] for rec in cs_new_data]
cs_rates = [rec[1] for rec in cs_new_data]

plt.plot(cs_rates, cs_accs, color="red", marker="*", markersize=7, label="CiteSeer")
plt.plot(cora_rates, cora_accs, color="green", marker="o", markersize=7, label="Cora")
plt.xlabel("Masked node feature rate [0, 1.0]")
plt.ylabel("Test accuracy %")
plt.title("DGI on missing node features")
plt.legend()
plt.show()