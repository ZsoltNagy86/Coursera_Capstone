#!/usr/bin/env python
# coding: utf-8

# # <span style="color:purple">Segmenting and Clustering Neighborhoods in Toronto</span>

# ### <span style="color:darkred">Importing packages</span>

# In[1]:


# Importing general packages
import pandas as pd
import dfply

from dfply import *
import numpy as np

# Importing packages for vizualization
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
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
#!conda install -c conda-forge geocoder --yes 
import geocoder
#!conda install -c conda-forge geopy --yes 
from geopy.geocoders import Nominatim
import folium # map rendering library

# Packages for hiding sensitive data
from IPython.display import HTML

# Importing k-means from clustering stage
from sklearn.cluster import KMeans


# ### <span style="color:darkred">Scraping wiki page for data about Canada's Borough/span>

# In[2]:


html = requests.get('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M')

#turn the HTML into a soup text object
bs = BeautifulSoup(html.text, 'lxml')


# In[3]:


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


# In[4]:


print(df_n.shape)


# ### <span style="color:darkred">Adding geospatial data</span>

# In[5]:


# Reading Lat and Long for Postcodes
df_gsp = pd.read_csv('http://cocl.us/Geospatial_data')
df_gsp = df_gsp.rename(columns={"Postal Code": "Postcode"})
df_gsp.head()


# In[6]:


# Adding Lat and Long to df
df_n = df_n >> left_join(df_gsp, by = "Postcode")
df_n


# ### <span style="color:darkred"> Adding the most common venue categories in each neighborhood in Toronto </span>

# In[7]:


# Adding credentials for using Foursquare
import getpass

CLIENT_ID = getpass.getpass('Enter your Foursquare CLIENT_ID')
CLIENT_SECRET = getpass.getpass('Enter your Foursquare CLIENT_SECRET')
VERSION = '20180605'
LIMIT = 100

print('Your credentials are stored')


# ### <span style="color:darkred"> Filtering neighbourhoods that belongs to Toronto </span>

# In[8]:


### <span style="color:darkred"> Filtering neighbourhoods that belongs to Toronto </span># Filtering neighbourhoods
df_n_tor = df_n >> mask(X.Borough.str.contains('Toronto') == True)
df_n_tor


# In[9]:


#Definging function for using API of Foursquare
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
    nearby_venues.columns = ['Neighbourhood', 
                  'Neighbourhood_Latitude', 
                  'Neighbourhood_Longitude', 
                  'Venue', 
                  'Venue_Latitude', 
                  'Venue_Longitude', 
                  'Venue_Category']
    
    return(nearby_venues)


# In[10]:


# Creating Df by adding vanues to df of Toronto's Boroughs
df_Tor_venues = getNearbyVenues(df_n_tor['Neighbourhood'], df_n_tor['Latitude'], df_n_tor['Longitude'], 500)

df_Tor_venues.head(10)


# ### <span style="color:darkred"> Encoding df containing info about nearby venues </span>

# In[89]:


# One hot encoding for calculating frequency
toronto_onehot = pd.get_dummies(df_Tor_venues[['Venue_Category']], prefix="", prefix_sep="")

# Adding neighborhood column back to dataframe
toronto_onehot['Neighbourhood'] = df_Tor_venues['Neighbourhood']
fixed_columns = [toronto_onehot.columns[-1]] + list(toronto_onehot.columns[:-1])
toronto_onehot = toronto_onehot[fixed_columns]

#calculating frequencies
toronto_grouped = toronto_onehot.groupby('Neighbourhood').mean().reset_index()
toronto_grouped


# ### <span style="color:darkred"> Checking the most frequent venues by Neigbourhoods </span>

# In[90]:


df_Tor_venues_grouped = df_Tor_venues >> group_by(X.Neighbourhood, X.Venue_Category) >> summarize(Count = X.Venue_Category.count()) >> select(X.Neighbourhood, X.Venue_Category, X.Count)
df_Tor_venues_grouped = df_Tor_venues_grouped.sort_values(by=['Neighbourhood','Count'], ascending=[True, False])
df_Tor_venues_grouped


# In[91]:


# Selecting the first 10 most frequent Vanue Category by Neighbourhood
df_venue = pd.DataFrame() #creates a new dataframe that's empty

for element in df_Tor_venues_grouped.Neighbourhood.unique():
    df_container = df_Tor_venues_grouped >> mask(X.Neighbourhood == element)
    if len(df_container) < 10:
        df_venue = df_venue.append(df_container)
    if len(df_container) >= 10:
        df_venue = df_venue.append(df_container.head(10))
df_venue


# In[92]:


# Adding geo data to the data frame
df_venue = df_venue >> left_join(df_n, by="Neighbourhood")
df_venue


# In[93]:


### <span style="color:darkred"> Clustering neighbourhoods based on most frequent venue types </span>


# In[94]:


# set number of clusters
kclusters = 4

toronto_grouped_clustering = toronto_grouped.drop('Neighbourhood', 1)

# run k-means clustering
kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(toronto_grouped_clustering)

# check cluster labels generated for each row in the dataframe
kmeans.labels_[0:100]


# In[95]:


# Creating dataframe for storing cluster label of Neighbourhoods
toronto_clusters = toronto_grouped >> mutate(Clusters = kmeans.labels_) >> select(X.Neighbourhood, X.Clusters)
toronto_clusters


# In[96]:


# Adding clusters to Df venue
df_venue = df_venue >> left_join(toronto_clusters, by="Neighbourhood")
df_venue


# In[97]:


# Creating data_frame for mapping
df_toronto = df_venue >> drop(X.Venue_Category, X.Count) >> distinct(X.Neighbourhood)
df_toronto = df_toronto.reset_index(drop=True)
df_toronto


# ### <span style="color:darkred"> Mapping clusters </span>

# In[98]:


# Finding geospatial data of Toronto
address = 'Toronto, CA'

geolocator = Nominatim(user_agent="tor_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Toronot are {}, {}.'.format(latitude, longitude))


# In[99]:


# create map
map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = np.arange(kclusters)
ys = [i + x + (i*x)**2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# add markers to the map
markers_colors = []
for lat, lon, poi, cluster in zip(df_toronto['Latitude'], df_toronto['Longitude'], df_toronto['Neighbourhood'], df_toronto['Clusters']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster-1],
        fill=True,
        fill_color=rainbow[cluster-1],
        fill_opacity=0.7).add_to(map_clusters)
       
map_clusters


# ### <span style="color:darkred"> Exploring Clusters </span>

# In[100]:


# Checking most frequent venues in Cluster 1
df_venue >> mask(X.Clusters == 0) >> select(X.Venue_Category) >> distinct(X.Venue_Category)


# In[101]:


# Checking most frequent venues in Cluster 2
df_venue >> mask(X.Clusters == 1) >> select(X.Venue_Category) >> distinct(X.Venue_Category)


# In[102]:


# Checking most frequent venues in Cluster 3
df_venue >> mask(X.Clusters == 2) >> select(X.Venue_Category) >> distinct(X.Venue_Category)


# In[103]:


# Checking most frequent venues in Cluster 4
df_venue >> mask(X.Clusters == 3) >> select(X.Venue_Category) >> distinct(X.Venue_Category)

