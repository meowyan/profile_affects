import numpy as np
import pandas as pd
import os
import sys
sys.path.append(os.path.abspath(''))
print(sys.path)
import util

def categorical(mapper, arr):
    retval = list(map(mapper.get, arr))
    retval = [a if a is not None else -1.0 for a in retval] ## handling "Others"
    return retval

def numerical(range_map, arr):
    def get_cat(range_map, x):
        for key in range_map:
            if key[0] <= x <= key[1]:
                return range_map[key]
    retval = [get_cat(range_map, a) for a in arr]
    return retval

# load pinfo
pinfo = pd.read_pickle('data/pinfo.pkl')
print(list(pinfo))

# range_map will result in about 2108 -1, 756 -0.33, 913 0.33, 42 1... 
range_map = {(0,20):-1.0, (21,30):-0.33, (31,40):0.33, (41,80):1.0}
range_map1 = {(0,20):-1.0, (21,80):1.0} # perhaps i should consider using this instead??
age = pinfo['age'].to_numpy()
age = numerical(range_map, age)
# age = dh.normalize(age, min(age), max(age))

mapper = {'US': 1.0, 'IN': 0.0}
country_encul = pinfo['country_enculturation'].to_numpy()
country_encul = categorical(mapper, country_encul)

country_live = pinfo['country_live'].to_numpy()
country_live = categorical(mapper, country_live)

mapper = {'EN': 1.0, 'TA': 0.0}
language = pinfo['fav_music_lang'].to_numpy()
language = categorical(mapper, language)

mapper = {'Male': 1.0, 'Other': 0.0, 'Female': -1}
gender = pinfo['gender'].to_numpy()
gender = categorical(mapper, gender)

mapper = {'Rock': 1.0, 'Pop': 0.33, 'Classical music': -0.33}
genre = pinfo['fav_genre'].to_numpy()
genre = categorical(mapper, genre)

mapper = {'Yes': 1.0, 'No': 0.0}
instrument = pinfo['play_instrument'].to_numpy()
instrument = categorical(mapper, instrument)

training = pinfo['training'].to_numpy()
training = categorical(mapper, training)

range_map = {(0,0):-1.0, (1,5):0.0, (6,50):1.0}
training_dur = pinfo['training_duration'].to_numpy()
training_dur = [int(a) for a in training_dur]
training_dur = numerical(range_map, training_dur)
# training_dur = dh.normalize(training_dur, min(training_dur), max(training_dur))


temp = {
    'workerid': pinfo['workerid'],
    'master': pinfo['master'],
    'age': age,
    'country_enculturation': country_encul,
    'country_live': country_live,
    'fav_music_lang': language,
    'gender': gender,
    'fav_genre': genre,
    'play_instrument': instrument,
    'training': training,
    'training_duration': training_dur
    }
df = pd.DataFrame(temp)
print(df.head())
print(pinfo.head())

df.to_pickle(os.path.join(os.path.abspath(''), 'data', 'pinfo_numero.pkl'))

'''
min age: 7
max age: 72
##   <=20   21-30   31-40   >40

country_live = pinfo['country_live'].to_numpy()
# print(country_live[0:10])
## US, IN, Other

language = pinfo['fav_music_lang'].to_numpy()
# print(language[0:10])
## EN, TA, Other


gender = pinfo['gender'].to_numpy()
# print(gender[0:10])
## Female, Male, Other

genre = pinfo['fav_genre'].to_numpy()
# print(genre[0:10])
## Rock Pop Classical Other
##   1  .33   -.33     -1

instrument = pinfo['play_instrument'].to_numpy()
# print(instrument[0:10])
## Yes No 1 0 

training = pinfo['training'].to_numpy()
# print(training[0:10])
## Yes No 1 0 

training_dur = pinfo['training_duration'].to_numpy()
# print(training_dur[0:10])
## num years
min duration: 0
max duration: 31
(mostly 0, or 10, and in between. only one 31...)
##   0   1-5   >5
'''

# temp = {'age': age, 'country_enculturation': meow}
# df = pd.DataFrame(temp)
# print(df)