import pandas as pd
import numpy as np
import json
import gzip
import math
import random
from datetime import datetime
from collections import Counter
#import matplotlib.pyplot as plt
#import seaborn as sns
import os
import pickle as pkl
import re
import scipy
import statsmodels.formula.api as smf
import liwc
lexicon, category_names = liwc.read_dic('/shared/3/projects/agrimaTwitter/LIWC2015_English.dic')

os.chdir('/shared/3/projects/style-influence/')

def fix_outlier(x):
    lower_bound = np.percentile(x,0.25) - 3*scipy.stats.iqr(x)
    upper_bound = np.percentile(x,0.75) + 3*scipy.stats.iqr(x)
    x[x>upper_bound] = upper_bound
    x[x<lower_bound] = lower_bound
    return x

def standardize(x):
    return (x - np.mean(x)) / np.std(x)

print(datetime.now())
df = pkl.load(open('data/conversation-turns-tokenized-aba/RC_2019-12-00.pkl', 'rb'))
print(datetime.now())

df['len_a'] = df['tokens_liwc_parent'].apply(lambda x: x['length'] if type(x)!=float else 0)
df['len_b'] = df['tokens_liwc'].apply(lambda x: x['length'])
N = sum(df['len_a']) + sum(df['len_b'])

df['len_a'] = standardize(df['len_a'])
df['len_a'] = fix_outlier(df['len_a'])

df['len_b'] = standardize(df['len_b'])
df['len_b'] = fix_outlier(df['len_b'])

df['parent_score'][df['parent_score'].isna()] = 0
df['parent_score'][df['parent_score']==''] = 0
df['parent_score'] = df['parent_score'].astype(int)
df['parent_score'] = standardize(df['parent_score'])
df['parent_score'] = fix_outlier(df['parent_score'])

df['score'] = standardize(df['score'])
df['score'] = fix_outlier(df['score'])

df['depth'] = standardize(df['depth'])
df['depth'] = fix_outlier(df['depth'])


pd.options.mode.chained_assignment = None
all_cats = []
for mtype in category_names:
    try:
        print(datetime.now(), mtype)
        df['marker_a'] = df['tokens_liwc_parent'].apply(lambda x: x[mtype] if type(x)!=float else 0)
        df['marker_b'] = df['tokens_liwc'].apply(lambda x: x[mtype])
        n_a = sum(df['marker_a'])
        n_b = sum(df['marker_b'])

        df['marker_a'] = standardize(df['marker_a'])
        df['marker_a'] = fix_outlier(df['marker_a'])
        df['marker_b'] = standardize(df['marker_b'])
        df['marker_b'] = fix_outlier(df['marker_b'])
        #df['marker_a'] = df['marker_a']/df['len_a']
        #df['marker_b'] = df['marker_b']/df['len_b']

        mod = smf.ols('marker_b ~ marker_a * parent_controversiality + len_a + len_b + \
                        parent_score + score + depth + controversiality', 
                      data=df[df.parent_id!='']).fit()

        metrics = mod.conf_int()
        metrics = metrics[metrics.index.isin(['marker_a','marker_a:parent_controversiality[T.1]'])]
        metrics.columns = ['lo','hi']
        metrics['mean'] = mod.params[['marker_a','marker_a:parent_controversiality[T.1]']]
        metrics['p'] = mod.pvalues[['marker_a','marker_a:parent_controversiality[T.1]']]
        metrics['var'] = mtype
        metrics['num_a'] = n_a
        metrics['num_b'] = n_b
        all_cats.append(metrics)
    except Exception as e:
        print(e)
        
pd.options.mode.chained_assignment = 'warn'

all_cats_df = pd.concat(all_cats).reset_index()

pivoted = all_cats_df.pivot(index="var", columns="index", values="mean").reset_index()
pivoted.columns = ['var','baseline','net_effect']
pivoted['relative_effect'] = pivoted['net_effect'] / pivoted['baseline']
pivoted = pivoted.sort_values('relative_effect')
pivoted['x'] = list(range(73))
pivoted['x'] = pivoted['x'] - 36
pivoted['var'] = pivoted['var'].apply(lambda x: re.sub('.*\(|\).*','',x))


min_odds = -0.5
max_odds = 0.5
sig_val = 0
#x_vals = list(pivoted['x'])
import random
x_vals = random.sample(list(pivoted['x']), pivoted.shape[0])
#x_vals = [max(v,-0.1) for v in x_vals] 
#x_vals = [min(v,0.1) for v in x_vals] 
y_vals = list(pivoted['relative_effect'])
y_vals = [max(v,min_odds) for v in y_vals] 
y_vals = [min(v,max_odds) for v in y_vals]
sizes = [min(20,np.sqrt(3000*abs(v))) for v in y_vals]
neg_color, pos_color, insig_color = ('green', 'purple', 'grey')
colors = []
annots = []
pos_list={}
neg_list={}

for index, row in pivoted.iterrows():
    if row['relative_effect'] > sig_val:
        colors.append(pos_color)
        annots.append(row['var'])
        pos_list[row['var']]=row['relative_effect']
    elif row['relative_effect'] < -sig_val:
        colors.append(neg_color)
        annots.append(row['var'])
        neg_list[row['var']]=row['relative_effect']
    else:
        colors.append(insig_color)
        annots.append(None)

fig, ax = plt.subplots(figsize=(10,10))
ax.scatter(x_vals, y_vals, c=colors, linewidth=0,s=1)
for i, annot in enumerate(annots):
    ax.annotate(annot, (x_vals[i], y_vals[i]), color=colors[i],size=sizes[i])
#ax.set_xscale('log')
#ax.set(xlim=(0.8e-4, 2*10e-2))
ax.set(ylim=(-0.6, 0.6))
ax.set_xlabel('random',fontsize=20)
ax.set_ylabel('relative effect',fontsize=20)
ax.set_yscale('symlog',linthreshy=15)



