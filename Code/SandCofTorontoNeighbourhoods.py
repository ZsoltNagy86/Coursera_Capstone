#!/usr/bin/env python
# coding: utf-8

# # <span style="color:purple">Segmenting and Clustering Neighborhoods in Toronto</span>

# ### <span style="color:darkred">Importing packages</span>

# In[2]:


# Importing general packages
import pandas as pd

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


# In[88]:


html = requests.get('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M')

#turn the HTML into a soup text object
bs = BeautifulSoup(html.text, 'lxml')


# In[94]:


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

#Reindexing the DataFrame
df_n = df_n.reset_index(drop=True)

#Checking the dataframe
df_n


# In[66]:





# In[ ]:




