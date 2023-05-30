import pickle
from collections import defaultdict
from glob import glob

import pandas as pd
from tqdm import tqdm

DATA_DIRECTORY = '/shared/3/projects/style-influence/data/aparna-conversation-thread-aba/'

month_files = glob(DATA_DIRECTORY + "*.pkl")

print(len(month_files))

unique_users_fp = '/shared/3/projects/style-influence/data/user-tenures/unique_conversational_users.pkl'

with open(unique_users_fp, 'rb') as f:
    users = pickle.load(f)

print(len(users))

unique_subreddits_fp = '/shared/3/projects/style-influence/data/user-tenures/unique_conversational_subreddits.pkl'

with open(unique_subreddits_fp, 'rb') as f:
    subreddits = pickle.load(f)

print(len(subreddits))

user_sub_ts = defaultdict(lambda: defaultdict(tuple))
out_df = '/shared/3/projects/style-influence/data/user-tenures/tenures.pkl'


def to_df(user_sub_ts):
    rows = []
    for user, subreddit_ts in tqdm(user_sub_ts.items(), total=len(user_sub_ts)):
        for subreddit, (first_post, last_post) in subreddit_ts.items():
            rows.append({
                'author': user,
                'subreddit': subreddit,
                'first_post_utc': first_post,
                'last_post_utc': last_post,
                'tenure': last_post - first_post
            })
    return pd.DataFrame(rows)


for month_file in tqdm(month_files, total=len(month_files)):
    print("Reading in file: " + month_file)
    df = pd.read_pickle(month_file)
    df = df[['author', 'subreddit', 'created_utc']]
    print("Filtering the subreddit and users")
    df = df[df['subreddit'].isin(subreddits)]
    df = df[df['author'].isin(users)]
    print("Iterating through the timestamps")
    for row in df.itertuples():
        user, subreddit, created_utc = row.author, row.subreddit, row.created_utc
        if user in user_sub_ts and subreddit in user_sub_ts[user]:
            first_post, last_post = user_sub_ts[user][subreddit]

            if created_utc < first_post:
                first_post = created_utc

            if created_utc > last_post:
                last_post = created_utc

            user_sub_ts[user][subreddit] = (first_post, last_post)
        else:
            user_sub_ts[user][subreddit] = (created_utc, created_utc)

tenure_df = to_df(user_sub_ts)
print("Total user/subreddit combos")
print(len(tenure_df))
print("Saving tenures to : " + out_df)
tenure_df.to_pickle(out_df)
