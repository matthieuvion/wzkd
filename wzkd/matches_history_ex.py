# # used for caching results of functions, particularly the calls made to the API, in case of failures etc
# from sklearn.externals.joblib import Memory 
# # memory1 = Memory(location='/tmp', verbose=0)
# # memory2 = Memory(location='/tmp', verbose=0)
# # memory3 = Memory(location='/tmp', verbose=0)
# 
# 

# tsLastGame = '0'
# matchesFound = True
# matches = []
# while matchesFound:
#     resp_matches = s.get('https://www.callofduty.com/api/papi-client/crm/cod/v2/title/mw/platform/battle/gamer/Vioo%2321794/matches/wz/start/0/end/' + str(tsLastGame) + '000/details?limit=20')
#     if len(resp_matches.json()['data']['matches']) == 20:
#         new_matches = resp_matches.json()['data']['matches']
#         tsLastGame = new_matches[-1]['utcStartSeconds']
#         matches += new_matches
#     else:
#         matchesFound = False
#     time.sleep(0.2)
#         
# len(matches)
# 

# # @memory1.cache
# def search_get_posts(pid, start_date, end_date, start, **filters):
#     """
#     Get 250 posts
#     """    
#     # default payload
#     default_p = {
#         "tz": "UTC",
#         "clause": {"and":[{"withRT": False}]},
#         "fctx": [],
#         "from":start_date.isoformat(),
#         "to":end_date.isoformat(),
#         "pagination": {"sortBy": "date", "sortOrder": "asc","limit": 250,"start": start}
#     }
#     # update with optional arguments (**kwargs)
#     p = copy.deepcopy(default_p)
#     for k, v in filters.items():
#         if k:
#             if k in ['or', 'focuses', 'corpora','platforms', 'customFields',
#                      'query', 'followers', 'languages', 'countries', 'tones']:
#                 p["clause"]["and"].append({k:v})
#             elif k == 'not': # ex. not-filter format must be "not": [{"corpora": [29436]}, {"focuses": [226634]}]
#                 for item in v:
#                     p["clause"]["and"].append({"not":item}) 
#             else:
#                 p[k] = v
#     time.sleep(random.uniform(0.70, 0.85))  
#     res = post_method(token, '/projects/{pid}/inbox/search.json'.format(pid=pid), p)
#     n_posts = res['total']
#     df = pd.DataFrame(res['hits'])
#     return df, n_posts
# 
# @timer
# def search_get_all_posts(pid, start_date, end_date, **filters):
#     """
#     Get all batches of 250 posts
#     """
#     end_date = end_date + timedelta(days = 1) - timedelta(seconds = 1)
#     start = 0 # pagination (0 to first 250 results)
#     data, n_posts_first_call = search_get_posts(pid, start_date, end_date, start, **filters)
#     reservoir = n_posts_first_call
#     n_batches = math.ceil(n_posts_first_call/10000)
#     print('Getting posts from {} to {}\nThere are {} posts to collect : {} batches of (max) 10k posts\n'.format
#           (start_date, end_date, n_posts_first_call, n_batches))
#     
#     # Will run until all posts/batches have been gathered 
#     all_batches_10k = []
#     while len(data) >= 250:
#         batch_10k  = []
#         # API returns max 10K posts (0 to 200, etc.) before throwing error
#         while start < 10000:
#             data, n_posts = search_get_posts(pid, start_date, end_date, start, **filters)
#             batch_10k.append(data)
#             print('\rBatch {}/{} (> start: {}) | Posts {}-{}/{} | Reservoir {}/{}'.
#                   format(len(all_batches_10k)+1, n_batches, start_date,
#                          start, start + 250, 10000, reservoir, n_posts_first_call),  end='')
#             start += 250
#             reservoir -= 250
#             reservoir = 0 if reservoir <=250 else reservoir
#         batch_10k = pd.concat(batch_10k, axis=0, sort=False)
#         # batch_10k_detailed = details_df(batch_10k)
#         # all_batches_10k.append(batch_10k_detailed)
#         all_batches_10k.append(batch_10k)
#         start = 0 # start again at 0-250 results with updated new start_date (so we are below 10k posts thresh)
#         # new_start = pd.to_datetime(batch_10k_detailed.date.max()) # get last date when 10k posts is reached, it's our new start
#         new_start = pd.to_datetime(batch_10k.date.max())
#         start_date = new_start
#     posts = pd.concat(all_batches_10k, axis=0, sort=False)
#     return posts

