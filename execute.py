import numpy as np
import scipy.sparse as sp
import torch
import torch.nn as nn
import argparse
import json
from models import DGI, LogReg
from utils import process

parser = argparse.ArgumentParser(description='Process CLI args for data damage rate')
parser.add_argument('--dmgrate', type=float, required=True)
args = parser.parse_args()

dataset = 'pubmed'
device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")

# training params
batch_size = 1
nb_epochs = 10000
patience = 20
lr = 0.001
l2_coef = 0.0
drop_prob = 0.0
hid_units = 512
sparse = True
nonlinearity = 'prelu' # special name to separate parameters

adj, features, labels, idx_train, idx_val, idx_test = process.load_data(dataset)
features, _ = process.preprocess_features(features)

nb_nodes = features.shape[0]
ft_size = features.shape[1]
nb_classes = labels.shape[1]

adj = process.normalize_adj(adj + sp.eye(adj.shape[0]))

if sparse:
    sp_adj = process.sparse_mx_to_torch_sparse_tensor(adj)
else:
    adj = (adj + sp.eye(adj.shape[0])).todense()

features = torch.FloatTensor(features[np.newaxis])
if not sparse:
    adj = torch.FloatTensor(adj[np.newaxis])
labels = torch.FloatTensor(labels[np.newaxis])
idx_train = torch.LongTensor(idx_train)
idx_val = torch.LongTensor(idx_val)
idx_test = torch.LongTensor(idx_test)

cur_dmg_ratio = float(args.dmgrate)
print ("Rate:", cur_dmg_ratio)
features = process.get_missing_feature_mask(features, cur_dmg_ratio)
assert features.size(0) == 1, "Feature size mismatch"

model = DGI(ft_size, hid_units, nonlinearity)
optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=l2_coef)

if torch.cuda.is_available():
    print ('Using CUDA')
    model.to(device)
    features = features.to(device)
    if sparse:
        sp_adj = sp_adj.to(device)
    else:
        adj = adj.to(device)
    labels = labels.to(device)
    idx_train = idx_train.to(device)
    idx_val = idx_val.to(device)
    idx_test = idx_test.to(device)

b_xent = nn.BCEWithLogitsLoss()
xent = nn.CrossEntropyLoss()
cnt_wait = 0
best = 1e9
best_t = 0

for epoch in range(nb_epochs):
    model.train()
    optimiser.zero_grad()

    idx = np.random.permutation(nb_nodes)
    shuf_fts = features[:, idx, :]

    lbl_1 = torch.ones(batch_size, nb_nodes)
    lbl_2 = torch.zeros(batch_size, nb_nodes)
    lbl = torch.cat((lbl_1, lbl_2), 1)

    if torch.cuda.is_available():
        shuf_fts = shuf_fts.to(device)
        lbl = lbl.to(device)
    
    logits = model(features, shuf_fts, sp_adj if sparse else adj, sparse, None, None, None) 
    loss = b_xent(logits, lbl)

    if epoch % 200 == 0:
        print (f'Epoch: {epoch:<5} | Loss: {loss.item()}')

    if loss < best:
        best = loss
        best_t = epoch
        cnt_wait = 0
        torch.save(model.state_dict(), f'{dataset}_best_models/best_dgi_{cur_dmg_ratio}.pkl')
    else:
        cnt_wait += 1

    if cnt_wait == patience:
        print ('Early stopping!')
        break

    loss.backward()
    optimiser.step()

print ('Loading {}th epoch'.format(best_t))
model.load_state_dict(torch.load(f'{dataset}_best_models/best_dgi_{cur_dmg_ratio}.pkl'))

embeds, _ = model.embed(features, sp_adj if sparse else adj, sparse, None)
train_embs = embeds[0, idx_train]
val_embs = embeds[0, idx_val]
test_embs = embeds[0, idx_test]

train_lbls = torch.argmax(labels[0, idx_train], dim=1)
val_lbls = torch.argmax(labels[0, idx_val], dim=1)
test_lbls = torch.argmax(labels[0, idx_test], dim=1)

tot = torch.zeros(1)
tot = tot.to(device)

accs = []

for _ in range(50):
    log = LogReg(hid_units, nb_classes)
    opt = torch.optim.Adam(log.parameters(), lr=0.01, weight_decay=0.0)
    log.to(device)

    pat_steps = 0
    best_acc = torch.zeros(1)
    best_acc = best_acc.to(device)
    for _ in range(100):
        log.train()
        opt.zero_grad()

        logits = log(train_embs)
        loss = xent(logits, train_lbls)
        
        loss.backward()
        opt.step()

    logits = log(test_embs)
    preds = torch.argmax(logits, dim=1)
    acc = torch.sum(preds == test_lbls).float() / test_lbls.shape[0]
    accs.append(acc * 100)
    print (acc)
    tot += acc

print (f'Average accuracy for DR = {cur_dmg_ratio}: {tot / 50}')
accs = torch.stack(accs)
print (f'Accuracy mean: {accs.mean()}')
print (f'Accuracy std: {accs.std()}')

final_data = {
    "damage_rate": cur_dmg_ratio,
    "accuracy": (tot / 50).item(),
    "acc_mean": accs.mean().item(),
    "acc_std": accs.std().item(),
    "best_model_path": f'{dataset}_best_models/best_dgi_{cur_dmg_ratio}.pkl',
    "best_t": best_t
}

print (final_data)

with open(f"{dataset}_stats/stats-{cur_dmg_ratio}.json", "a") as f:
    json.dump(final_data, f)
