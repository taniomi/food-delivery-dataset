import pandas as pd
import numpy as np
import re
from haversine import haversine
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import folium
import streamlit as st

def clean_df(df):
    """
    Receives dataframe df and cleans it.
        
        Steps of cleaning:
            1. Time_taken(min) column
            2. Excludes 'NaN ' and spaces
            3. Type conversion
            4. Creates Week_Year column

        Parameters:
            df : pandas dataframe

        Outputs:
            df : pandas dataframe
    """
    # 1
    df['Time_taken(min)'] = (df['Time_taken(min)']
                             .apply(lambda x: x.split(' ')[1])
                             .astype(int))
    # 2
    for col in df.columns:
        df = df.loc[df.loc[:,col] != 'NaN ',:]

    cols_to_clean = ['ID',
                     'Delivery_person_ID',
                     'Road_traffic_density',
                     'Type_of_order',
                     'Type_of_vehicle',
                     'Festival',
                     'City']

    for col in cols_to_clean:
        df[col] = df[col].str.strip()
    # 3
    df['Delivery_person_Age'] = df['Delivery_person_Age'].astype(int)
    df['Delivery_person_Ratings'] = df['Delivery_person_Ratings'].astype(float)
    df['Order_Date'] = pd.to_datetime(df['Order_Date'], format='%d-%m-%Y')
    df['multiple_deliveries'] = df['multiple_deliveries'].astype(int)
    # 4
    df['Week_Year'] = df['Order_Date'].dt.strftime('%U')

    return df



def filters_df(df):
    filter_date = st.sidebar.slider('Choose dates:',
                                    value=datetime(2022, 4, 13),
                                    min_value=datetime(2022, 2, 11),
                                    max_value=datetime(2022, 4, 6),
                                    format='DD-MM-YY')
    filter_traffic = st.sidebar.multiselect('Choose traffic conditions:',
                                            ['Low','Medium','High','Jam'],
                                            default=['Low','Medium','High','Jam'])

    return df[(df['Order_Date'] < filter_date) & (df['Road_traffic_density'].isin(filter_traffic))]



###############################################################################
#                       BUSINESS VIEW                                         #
###############################################################################
def fest_time(df, festival):
    festival_time = df.loc[df.loc[:, 'Festival'] == festival, 'Time_taken(min)']

    return festival_time



def calc_mean_dist(df):
    dfaux = (df.loc[:, 
                   ['Restaurant_latitude', 
                    'Restaurant_longitude', 
                    'Delivery_location_latitude', 
                    'Delivery_location_longitude']])
    dfaux['Distance'] = (dfaux.apply(lambda x: 
                         haversine((x['Restaurant_latitude'], 
                                    x['Restaurant_longitude']), 
                                   (x['Delivery_location_latitude'], 
                                    x['Delivery_location_longitude'])), 
                         axis=1))
    mean_dist = dfaux['Distance'].mean()

    return mean_dist



def plot_fig_mean_dist(df):
    df = (df.loc[:, 
                 ['City',
                 'Restaurant_latitude', 
                 'Restaurant_longitude', 
                 'Delivery_location_latitude', 
                 'Delivery_location_longitude']])
    df['Distance'] = (df.apply(lambda x: 
                         haversine((x['Restaurant_latitude'], 
                                    x['Restaurant_longitude']), 
                                   (x['Delivery_location_latitude'], 
                                    x['Delivery_location_longitude'])),
                         axis=1))
    mean_dist = (df.loc[:, ['City', 'Distance']]
                   .groupby('City')
                   .mean()
                   .reset_index())
    fig_mean_dist = go.Figure(data=[go.Pie(labels=mean_dist['City'],
                                           values=mean_dist['Distance'],
                                           hole=0.5)])
    return st.plotly_chart(fig_mean_dist)



def plot_fig_time_city(df):
    dfaux = (df.loc[:, ['City', 'Time_taken(min)']]
               .groupby('City')
               .agg({'Time_taken(min)': ['mean', 'std']})
               .reset_index())
    dfaux.columns = ['City', 'Mean_time', 'Std_deviation_time']
    fig_time_city = go.Figure()
    fig_time_city.add_trace(go.Bar(name='Control',
                                   x=dfaux['City'],
                                   y=dfaux['Mean_time'],
                                   error_y=dict(type='data',
                                   array=dfaux['Std_deviation_time'])))
    fig_time_city.update_layout(barmode='group')

    return st.plotly_chart(fig_time_city)



def plot_fig_sun(df):
    dfaux = (df.loc[:, ['City', 'Road_traffic_density', 'Time_taken(min)']]
               .groupby(['City', 'Road_traffic_density'])
               .agg({'Time_taken(min)': ['mean', 'std']}))
    dfaux.columns = ['Time_mean', 'Time_std']
    dfaux = dfaux.reset_index()
    fig_sun = px.sunburst(dfaux,
                          path=['City', 'Road_traffic_density'],
                          values='Time_mean',color='Time_std',
                          color_continuous_scale='icefire',
                          color_continuous_midpoint=np.average(dfaux['Time_std']))
    return st.plotly_chart(fig_sun)



def plot_chart_week(df):
    pedidos_por_semana = (df.loc[:,['ID','Week_Year']]
                          .groupby('Week_Year')['ID']
                          .count().reset_index())
    chart_week = px.line(pedidos_por_semana,title='Orders per week',
                         x='Week_Year',y='ID',
                         height=350)
    return st.plotly_chart(chart_week)



def plot_chart_deliverer_wk(df):
    entregas_por_semana = (df.loc[:,['ID','Week_Year']]
                           .groupby('Week_Year')
                           .count().reset_index())
    entregadores_por_semana = (df.loc[:,['Delivery_person_ID','Week_Year']]
                               .groupby('Week_Year')
                               .nunique().reset_index())

    df_merge = pd.merge(entregas_por_semana, entregadores_por_semana, how='inner')
    df_merge['Order_by_deliverer'] = df_merge['ID'] / df_merge['Delivery_person_ID']

    chart_deliverer_wk = px.line(df_merge,title='Orders by deliverer per week',
                                 x='Week_Year',y='Order_by_deliverer',
                                 height=350)
    return st.plotly_chart(chart_deliverer_wk)
    


def map_city_loc_traffic(df):
    city_loc_traffic = (df.loc[:,['City','Road_traffic_density','Delivery_location_latitude','Delivery_location_longitude']]
                          .groupby(['City','Road_traffic_density'])
                          .median().reset_index())
    map = st.map(city_loc_traffic,
                 latitude='Delivery_location_latitude',
                 longitude='Delivery_location_longitude')
    return map



###############################################################################
#                       DELIVERER VIEW                                        #
###############################################################################
def df_mean_rating_by_deliv(df):
    mean_rating_by_deliv = (df.loc[:,['Delivery_person_ID', 'Delivery_person_Ratings']]
                              .groupby('Delivery_person_ID')
                              .mean()
                              .reset_index())
    return st.dataframe(mean_rating_by_deliv)



def df_mean_rating_by_traffic(df):
    mean_rating_by_traffic = (df[['Delivery_person_Ratings','Road_traffic_density']]
                                .groupby('Road_traffic_density')
                                .agg({'Delivery_person_Ratings': ['mean', 'std']}))
    mean_rating_by_traffic.columns = ['delivery_mean', 'delivery_std']
    mean_rating_by_traffic.reset_index()

    return st.dataframe(mean_rating_by_traffic)



def df_mean_rating_by_climate(df):
    mean_rating_by_climate = (df[['Delivery_person_Ratings','Weatherconditions']]
                                .groupby('Weatherconditions')
                                .agg({'Delivery_person_Ratings': ['mean', 'std']}))
    mean_rating_by_climate.columns = ['delivery_mean', 'delivery_std']
    mean_rating_by_climate.reset_index()

    return st.dataframe(mean_rating_by_climate)



def df_fastest_deliverers(df):
    dfaux = (df[['Delivery_person_ID', 'City', 'Time_taken(min)']]
               .groupby(['City', 'Delivery_person_ID']).min()
               .sort_values(['City', 'Time_taken(min)']).reset_index())
    dfaux1 = dfaux[dfaux.City == 'Metropolitian'].head(10)
    dfaux2 = dfaux[dfaux.City == 'Semi-Urban'].head(10)
    dfaux3 = dfaux[dfaux.City == 'Urban'].head(10)
    fastest_deliverers = pd.concat([dfaux1, dfaux2, dfaux3]).reset_index(drop=True)

    return st.dataframe(fastest_deliverers)



def df_slowest_deliverers(df):
    dfaux = (df[['Delivery_person_ID', 'City', 'Time_taken(min)']]
               .groupby(['City', 'Delivery_person_ID']).max()
               .sort_values(['City', 'Time_taken(min)'], ascending=False).reset_index())
    dfaux1 = dfaux[dfaux.City == 'Metropolitian'].head(10)
    dfaux2 = dfaux[dfaux.City == 'Semi-Urban'].head(10)
    dfaux3 = dfaux[dfaux.City == 'Urban'].head(10)
    slowest_deliverers = pd.concat([dfaux1, dfaux2, dfaux3]).reset_index(drop=True)

    return st.dataframe(slowest_deliverers)