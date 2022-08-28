import matplotlib.pyplot as plt
import numpy as np
import json, os

PATH = "cora_stats/"

accs = []
rates = []

for fle in os.listdir(PATH):
    path_string = PATH + fle
    with open(path_string, "r") as f:
        data = json.load(f)

    accs.append(data['acc_mean'])
    rates.append(data['damage_rate'])

assert len(accs) == len(rates)
new_data = [[accs[i], rates[i]] for i in range(len(accs))]
new_data.sort(key=lambda r : r[1])
accs = [rec[0] for rec in new_data]
rates = [rec[1] for rec in new_data]

plt.plot(rates, accs, color="green", marker="*", markersize=7)
plt.xlabel("Masked node feature rate [0, 1.0]")
plt.ylabel("Test accuracy %")
plt.title("DGI on missing node features (Citeseer)")
plt.show()