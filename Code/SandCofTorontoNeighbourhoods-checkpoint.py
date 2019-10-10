#!/usr/bin/env python
# coding: utf-8

# # <span style="color:purple">Segmenting and Clustering Neighborhoods in Toronto</span>

# ### <span style="color:darkred">Importing packages</span>

# In[3]:


# Importing general packages
import pandas as pd
import dfply

from dfply import *
import numpy as np

# Importing packages for vizualization
import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')
import seaborn as sns

# Importing packages for scraping
#!conda install -c conda-forge wikipedia --yes 
import wikipedia
#!conda install -c conda-forge requests --yes 
import requests
#!conda install -c conda-forge bs4 --yes 
from bs4 import BeautifulSoup

# Importing packages for handling gespatial data
get_ipython().system('conda install -c conda-forge geocoder --yes ')
import geocoder

# Packages for hiding sensitive data
from IPython.display import HTML


# In[4]:


html = requests.get('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M')

#turn the HTML into a soup text object
bs = BeautifulSoup(html.text, 'lxml')


# In[5]:


#Defining customized replace function
REPLACE_SEQUENCES = ['\n']

def custom_replace(s):
    for to_replace in REPLACE_SEQUENCES:
        s = s.replace(to_replace, '')
    return s.strip()

#Defining a list for the neighbourhoods 
n_list = []

#Filling the list
for i in bs.find_all(name = 'td'):
    n_list.append(custom_replace(i.get_text()))
    
#Find the last element of the table of neighbourhoods in the list
matches = [i for i,x in enumerate(n_list) if x=='Not assigned']

#Dropping elements from the list that is not part of the original wikipedia table
n_list = n_list[0:matches[-1]+1]

#Creating DataFrame from the list
n_list = np.array(n_list)
columns=['Postcode','Borough','Neighbourhood']
df_n = pd.DataFrame(np.reshape(n_list, (int(len(n_list)/3),3)),columns=columns)
df_n

#Dropping those rows where Borough is not Assigned
df_n = df_n.drop(df_n[df_n['Borough'] == 'Not assigned' ].index)

#Sorting the DataFrame
df_n.sort_values('Postcode')

#Reindexing the DataFrame
df_n = df_n.reset_index(drop=True)

#Handling those cases, where we have Borough without Neighbourhood assigned
for i in range(0,len(df_n['Neighbourhood'])):
    if df_n['Neighbourhood'][i] == 'Not assigned':
        df_n['Neighbourhood'][i] = df_n['Borough'][i]

#Combining Neighbourhood into one line that belongs to the same Postcode
duplicates = df_n['Postcode'].duplicated()
for i in range(0,len(duplicates)):
    if duplicates[i] == True:
        first_index = list(df_n['Postcode']).index(df_n['Postcode'][i])
        df_n['Neighbourhood'][first_index] += str(', ' + df_n['Neighbourhood'][i])

#Dropping rows that are duplicates in terms of postcodes
df_n = df_n[(duplicates==False)]

#Reindexing the DataFrame
df_n = df_n.reset_index(drop=True)

#Checking the dataframe
df_n


# In[6]:


print(df_n.shape)


# In[7]:


df_gsp = pd.read_csv('http://cocl.us/Geospatial_data')
df_gsp = df_gsp.rename(columns={"Postal Code": "Postcode"})
df_gsp.head()


# In[8]:


df_n = df_n >> left_join(df_gsp, by = "Postcode")
df_n


# ### <span style="color:darkred"> Adding the most common venue categories in each neighborhood in Toronto </span>

# In[16]:


import getpass

CLIENT_ID = getpass.getpass('Enter your Foursquare CLIENT_ID')
CLIENT_SECRET = getpass.getpass('Enter your Foursquare CLIENT_SECRET')
VERSION = '20180605'
LIMIT = 100

print('Your credentails are stored')


# In[20]:


def getNearbyVenues(names, latitudes, longitudes, radius=500):
    
    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        #print(name)
            
        # create the API request URL
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
            
        # make the GET request
        results = requests.get(url).json()["response"]['groups'][0]['items']
        
        # return only relevant information for each nearby venue
        venues_list.append([(
            name, 
            lat, 
            lng, 
            v['venue']['name'], 
            v['venue']['location']['lat'], 
            v['venue']['location']['lng'],  
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                  'Neighborhood Latitude', 
                  'Neighborhood Longitude', 
                  'Venue', 
                  'Venue Latitude', 
                  'Venue Longitude', 
                  'Venue Category']
    
    return(nearby_venues)


# ### <span style="color:darkred"> Filtering neighbourhoods that belongs to Toronto </span>

# In[11]:


df_n_tor = df_n >> mask(X.Borough.str.contains('Toronto') == True)
df_n_tor


# In[29]:


df_Tor_venues = getNearbyVenues(df_n_tor['Neighbourhood'], df_n_tor['Latitude'], df_n_tor['Longitude'], 500)
df_Tor_venues = df_Tor_venues.rename(columns={"Neighborhood Latitude": "Neighborhood_Latitude",
                                             "Neighborhood Longitude": "Neighborhood_Longitude",
                                             "Venue Latitude": "Venue_Latitude",
                                             "Venue Longitude": "Venue_Longitude",
                                             "Venue Category": "Venue_Category"})
df_Tor_venues.head(10)


# In[34]:


df_Tor_venues >> group_by(X.Neighborhood) >> summarize(Count = X.Venue_Category.count())


# In[48]:


df_Tor_venues = df_Tor_venues >> group_by(X.Neighborhood, X.Venue_Category) >> summarize(Count = X.Venue_Category.count()) >> arrange(X.Neighborhood, X.Count, ascending=False) 
df_Tor_venues

