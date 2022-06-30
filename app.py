# WebApp and related libraries
import requests
from PIL import Image
import streamlit as st
from streamlit_lottie import st_lottie

# Analysis and Visualization libraries
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.figure import Figure
#matplotlib inline

# Date and JSON Libraries
import isodate
import DateTime as dt
from IPython.display import JSON

#Google API
from googleapiclient.discovery import build

#NLP Libraries
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from wordcloud import WordCloud

st.set_page_config(page_title="Youtube Analysis", layout="wide", page_icon="🎥")

# ---- Youtube Animation ----

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie_anime = load_lottieurl("https://assets7.lottiefiles.com/packages/lf20_EAfMOs/Youtube.json")
st_lottie(lottie_anime, speed=1, height=200, key="initial")

# ---- Header ----

sns.set_style('darkgrid')
row0_spacer1, row0_1, row0_spacer2, row0_2, row0_spacer3 = st.columns((.1, 2, .2, 1, .1))

row0_1.title('Analyze Your YouTube Channel')
with row0_2:
    st.write('')
row0_2.subheader('A Streamlit Webapp by [Mahesh](http://Mahesh.Popsy.Site). Reach out to me on [Twitter](https://twitter.com/Mahesh_221)')

# ---- Row 1 ----

row1_spacer1, row1_1, row1_spacer2 = st.columns((.1, 3.2, .1))

with row1_1:
    st.markdown("Hey there! Welcome to Mahesh's Youtube Analysis App. This app pulls the data from Youtube API and analyzes it to give you insights about your channel. You can also see the data in a graph. ")
    st.markdown(
        "**To begin, please enter your Youtube API & Channel Id** 👇. Learn how to [create API key](https://youtu.be/D56_Cx36oGY) in less than 2 minute, __*Timestamp: (1:11 - 2:11) & (3:17 - 3:33)*__")

# ---- Row 2 ----

row2_spacer1, row2_1, row2_spacer2, row2_2, row2_spacer3 = st.columns((.1, 0.7, .1, 0.7, .1))

with row2_1:
    api = st.text_input('Enter your Youtube API Key', max_chars=39)

with row2_2:
    C_Id = st.text_input('Enter your Youtube Channel Id', max_chars=24)

# ---- Row 3 ----

row3_spacer1, row3_1, row3_spacer2 = st.columns((2, 1.3, 1))

with row3_1:
    Submit = st.button('Analyze')

# ---- App pause ----

Api_Key = api
if not Api_Key:
    st.warning('Please Enter Your API Key')
    st.stop()
else: pass

Channel_ID = C_Id
if not Channel_ID:
    st.warning('Please Enter Your Channel ID')
    st.stop()


# ---- API Call ----

api_key = str(Api_Key)
channel_id = str(Channel_ID)

api_service_name = "youtube"
api_version = "v3"
youtube = build(api_service_name, api_version, developerKey = api_key)

# ---- Function to get the channel data ----

def get_channel_stats(youtube, channel_id):

    all_data = []
    
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id= channel_id
    )
    response = request.execute()
    
    # loop through items
    for i in range(len(response['items'])):
        data = dict(channelName = response['items'][i]['snippet']['title'],
                    subscribers = response['items'][i]['statistics']['subscriberCount'],
                    views = response['items'][i]['statistics']['viewCount'],
                    totalVideos = response['items'][i]['statistics']['videoCount'],
                    playlistId = response['items'][i]['contentDetails']['relatedPlaylists']['uploads'])
        
        all_data.append(data)
    return pd.DataFrame(all_data)



#Function to get video ids from the channels.
def get_video_ids(youtube, playlist_id):
    
    video_ids = []
    
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults = 50
    )
    response = request.execute()
    
    for item in response['items']:
        video_ids.append(item['contentDetails']['videoId'])
        
    next_page_token = response.get('nextPageToken')
    while next_page_token is not None:
        request = youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId = playlist_id,
                    maxResults = 50,
                    pageToken = next_page_token)
        response = request.execute()

        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])

        next_page_token = response.get('nextPageToken')
        
    return video_ids

#Function to get Video data
def get_video_details(youtube, video_ids):
    all_video_info = []
    
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=','.join(video_ids[i:i+50])
        )
        response = request.execute() 

        for video in response['items']:
            stats_to_keep = {'snippet': ['channelTitle', 'title', 'description', 'tags', 'publishedAt'],
                             'statistics': ['viewCount', 'likeCount', 'favouriteCount', 'commentCount'],
                             'contentDetails': ['duration', 'definition', 'caption']
                            }
            video_info = {}
            video_info['video_id'] = video['id']

            for k in stats_to_keep.keys():
                for v in stats_to_keep[k]:
                    try:
                        video_info[v] = video[k][v]
                    except:
                        video_info[v] = None

            all_video_info.append(video_info)
    return pd.DataFrame(all_video_info)

# ---- Initialize the data ----

channel_stats = get_channel_stats(youtube, channel_id)
playlist_id = channel_stats['playlistId'][0]
video_ids = get_video_ids(youtube, playlist_id)
video_df = get_video_details(youtube, video_ids)

# ---- Data Preprocessing ----

video_df.drop('favouriteCount', axis=1, inplace=True)
df = video_df.copy()

df['viewCount'] = pd.to_numeric(df['viewCount'])
df['likeCount'] = pd.to_numeric(df['likeCount'])
df['commentCount'] = pd.to_numeric(df['commentCount']) 

zero_views = df.index[df['viewCount'] == 0].tolist()
df.drop(df.index[zero_views], inplace=True)

df['duration_secs'] = df['duration'].apply(lambda x: isodate.parse_duration(x))
df['duration_secs'] = df['duration_secs'].astype('timedelta64[s]')
df['duration_mins'] = df['duration_secs'] / 60
df.drop('duration', axis=1, inplace=True)

df['published_date'] = df['publishedAt'].str.split('T').str[0]   
df['published_time'] =  df['publishedAt'].str.split('T').str[1].str.split('Z').str[0]
df['published_date'] = pd.to_datetime(df['published_date'])
df['day_of_week'] = df['published_date'].dt.weekday
df['weekday'] = df['day_of_week'].map({0:'Mon', 1:'Tue', 2:'Wed', 3:'Thu', 4:'Fri', 5:'Sat', 6:'Sun'})
df.drop('publishedAt', axis=1, inplace=True)

df['published_in_hr'] = df['published_time'].str.split(':').str[0].astype(int)
df['publishedhr_in_IST'] = df['published_in_hr']+5

df['short_title'] = df['title'].apply(lambda x: x[:62])
df['tags_count'] = df['tags'].apply(lambda x: 0 if x is None else len(x))

subs = channel_stats['subscribers'][0]
subs1 = format(int(subs), ',d')
vid = channel_stats['totalVideos'][0]
vid1 = format(int(vid), ',d')
views = channel_stats['views'][0]
views1 = format(int(views), ',d')


# ---- Row Result ----
rowr_spacer1, rowr_1, rowr_spacer2 = st.columns((.1, 3.2, .2))

with rowr_1:
    if len(df) == 0:
        st.write('No videos found')
    else:
        st.header('Channel Statistics:')


# ---- Row 4 ----

line1_spacer1, line1_1, line1_spacer2, line1_2, line1_spacer3, line1_3, line1_spacer4, line1_4, line1_spacer5 = st.columns((.1, 0.8, 0.1, 0.7 , .1, 0.5, 0.1, 0.5, .1))   

with line1_1:
    st.metric('Channel Name ', channel_stats['channelName'][0])

with line1_2:
    st.metric('Subscribers ', subs1)
    
with line1_3:
    st.metric('Total Videos ', vid1)
    
with line1_4:
    st.metric('Total Views ', views1)

# ----- Row Slider ----

rows_space1, rows_1, rows_space2 = st.columns((.1,3.2,.1))

def df_filter(message,df):

        df = pd.DataFrame(df.sort_values(by='published_date').to_numpy(), index=df.index, columns=df.columns)
        df['viewCount'] = pd.to_numeric(df['viewCount'])
        df['likeCount'] = pd.to_numeric(df['likeCount'])
        df['commentCount'] = pd.to_numeric(df['commentCount']) 
        df['duration_secs'] = df['duration_secs'].astype(int)
        df['day_of_week'] = df['day_of_week'].astype(int)
        df['published_in_hr'] = df['published_in_hr'].astype(int)
        df['publishedhr_in_IST'] = df['publishedhr_in_IST'].astype(int)
        
        slider_1, slider_2 = st.slider('%s' % (message),0,len(df)-1,[0,len(df)-1],1) 

        s_date = str(df.iloc[slider_1,12]).replace('00:00:00','')
        start_date = s_date.strip()
        e_date = str(df.iloc[slider_2,12]).replace('00:00:00','')
        end_date = e_date.strip()
        
        st.info('From: **{}**    To: **{}**' .format(start_date,end_date))
        
        df = df.iloc[slider_1:slider_2+1][:].reset_index(drop=True)
        
        return df

with rows_1:
    df = df_filter('Move sliders to filter data from the Oldest video (on the left) To the latest video (on the rigth)',df)


# ---- view calculation ----

if df['viewCount'].mean() > 50000 and df['viewCount'].mean() < 1000000 :
        a = 100000
        ex = 'L'
elif df['viewCount'].mean() > 1000 and df['viewCount'].mean() < 50000:
    a = 1000
    ex = 'k'
elif df['viewCount'].mean() > 1000000:
    a = 1000000
    ex = 'M'
else: pass


if df['viewCount'].sort_values(ascending=True)[0:3].mean() < 10000:
    v = 1
    e = ""
elif df['viewCount'].sort_values(ascending=True)[0:3].mean() > 10000 and df['viewCount'].sort_values(ascending=True)[0:3].mean() < 40000:
    v = 1000
    e = 'k'
elif df['viewCount'].sort_values(ascending=True)[0:3].mean() > 40000 and df['viewCount'].sort_values(ascending=True)[0:3].mean() < 500000:
    v = 100000
    e = 'L'
elif df['viewCount'].min() > 500000 :
    v = 1000000
    e = 'M'
else: pass

if df['likeCount'].sort_values(ascending=True)[0:3].mean() < 10000:
    l = 1
    b = ""
elif df['likeCount'].sort_values(ascending=True)[0:3].mean() > 10000 and df['likeCount'].sort_values(ascending=True)[0:3].mean() < 50000:
    l = 1000
    b = 'k'
elif df['likeCount'].sort_values(ascending=True)[0:3].mean() > 50000 and df['likeCount'].sort_values(ascending=True)[0:3].mean() < 300000:
    l = 100000
    b = 'L'
else: pass
    
    
# ---- Row n ---- (n = number of videos)

rown_space1, rown_1, rown_space2, rown_2, rown_space3, rown_3, rown_space4, rown_4, rown_space5 = st.columns((.1, 0.8, 0.1, 0.7 , .1, 0.5, 0.1, 0.5, .1))

avg_views = format(int(round(df['viewCount'].mean())), ',d')
avg_likes = format(int(round(df['likeCount'].mean())), ',d')
avg_comments = format(int(round(df['commentCount'].mean())), ',d')

with rown_1:
    st.header('From Filtered Videos:')

with rown_2:
    st.metric('Average Views ', avg_views)

with rown_3:
    st.metric('Average Likes ', avg_likes)

with rown_4:
    st.metric('Average Comments ', avg_comments)


# ---- Row 5 ----

row5_space1, row5_1, row5_space2, row5_2, row5_space3 = st.columns((.1, 1, .1, 1, .1))

with row5_1:
    
    st.subheader('Highest Viewed Videos')
    
    fig = Figure()
    ax = fig.subplots()
    sns.barplot(x='short_title', y='viewCount',data =df.sort_values('viewCount', ascending=False)[0:10] , palette="viridis", ax=ax)
    ax.set_xlabel('Title')
    ax.set_ylabel('Views')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=270)
    ax.tick_params(axis='x', which='major', labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

with row5_2:
    
    st.subheader('Lowest Viewed Videos')
    
    fig = Figure()
    ax = fig.subplots()
    sns.barplot(x='short_title', y='viewCount',data =df.sort_values('viewCount', ascending=True)[0:10] , palette="flare", ax=ax)
    ax.set_xlabel('Title')
    ax.set_ylabel('Views')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=270)
    ax.tick_params(axis='x', which='major', labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/v) + e ))
    st.pyplot(fig)
    
# ---- Row 6 ----

row6_space1, row6_1, row6_space2, row6_2, row6_space3 = st.columns((.1, 1, .1, 1, .1))

with row6_1:
    
    st.subheader('Most Liked Videos')
    
    fig = Figure()
    ax = fig.subplots()
    sns.barplot(x='short_title', y='likeCount',data =df.sort_values('likeCount', ascending=False)[0:10] , palette="viridis", ax=ax)
    ax.set_xlabel('Title')
    ax.set_ylabel('Likes')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=270)
    ax.tick_params(axis='x', which='major', labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/1000) + 'k'))
    st.pyplot(fig)

with row6_2:
    
    st.subheader('Least Liked Videos')
    
    fig = Figure()
    ax = fig.subplots()
    sns.barplot(x='short_title', y='likeCount',data =df.sort_values('likeCount', ascending=True)[0:10] , palette="flare", ax=ax)
    ax.set_xlabel('Title')
    ax.set_ylabel('Likes')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=270)
    ax.tick_params(axis='x', which='major', labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/l) + b ))
    st.pyplot(fig)

# ---- Row6a ----

row6a_space1, row6a_1, row6a_space2 = st.columns((.1, 3.2, .1))

with row6a_1:

    Top_views = df.sort_values('viewCount', ascending=False)[0:10]
    Bottom_likes = df.sort_values('likeCount', ascending=True)[0:10]
    Bottom_views = df.sort_values('viewCount', ascending=True)[0:10]
    Top_likes = df.sort_values('likeCount', ascending=False)[0:10]

    df5 = pd.merge(Top_views, Top_likes, on="title", how='inner')
    df6 = pd.merge(Bottom_views, Bottom_likes, on="title", how='inner')

    top_percent = round(len(df5)/len(Top_views)*100)
    bottom_percent = round(len(df6)/len(Bottom_views)*100)

    st.markdown('- **It looks like {}% of the top viewed videos have the most likes and {}% of the bottom viewed videos have the least likes.**'.format(top_percent, bottom_percent))

# ---- Row 7 ----

row7_space1, row7_1, row7_space2, row7_2, row7_space3 = st.columns((.1, 1, .1, 1, .1))

with row7_1:
    
    st.subheader('Video uploads by Day')
    
    fig = Figure()
    ax = fig.subplots()
    sns.countplot(x='weekday',data =df.sort_values('day_of_week', ascending=True) , palette="mako", ax=ax)
    ax.set_xlabel('Published Day')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x) ))
    st.pyplot(fig)

with row7_2:
    
    st.subheader('Video uploads by Time')
    
    fig = Figure()
    ax = fig.subplots()
    sns.countplot(x='publishedhr_in_IST',data =df.sort_values('publishedhr_in_IST', ascending=True) , palette="magma", ax=ax)
    ax.set_xlabel('Published Hour (IST)')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x) ))
    st.pyplot(fig)

# ---- Row 8 ----

row8_space1, row8_1, row8_space2, row8_2, row8_space3 = st.columns((.1, 1, .1, 1, .1))

with row8_1:
    
    st.subheader('Violin Plot of Views')
    
    fig = Figure()
    ax = fig.subplots()
    sns.violinplot(x='channelTitle', y='viewCount',data = df ,palette="viridis", ax=ax)
    ax.set_ylabel('Views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

with row8_2:
    
    st.subheader('Box Plot of Views')
    
    fig = Figure()
    ax = fig.subplots()
    sns.boxplot(x='channelTitle', y='viewCount',data =df ,palette="flare", ax=ax)
    ax.set_ylabel('Views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

# ---- Row 9 ----

row9_space1, row9_1, row9_space2, row9_2, row9_space3 = st.columns((.1, 1, .1, 1, .1))

with row9_1:
    
    st.subheader('Likes vs Views Scatter Plot')
    
    fig = Figure()
    ax = fig.subplots()
    sns.scatterplot(x='likeCount', y='viewCount',data =df,hue='weekday', palette="rocket_r", ax=ax)
    ax.set_xlabel('Likes')
    ax.set_ylabel('Viewss')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

with row9_2:
    
    st.subheader('Comments vs Views Scatter Plot')
    
    fig = Figure()
    ax = fig.subplots()
    sns.scatterplot(x='commentCount', y='viewCount',data =df,hue='weekday', palette="flare", ax=ax)
    ax.set_xlabel('Comments')
    ax.set_ylabel('views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)
    
# ---- Row 10 ----

row10_space1, row10_1, row10_space2, row10_2, row10_space3 = st.columns((.1, 1, .1, 1, .1))

with row10_1:
    
    st.subheader('Duration vs Views Scatter Plot')
    
    fig = Figure()
    ax = fig.subplots()
    sns.scatterplot(x='duration_mins', y='viewCount',data =df,hue='weekday', palette="crest", ax=ax)
    ax.set_xlabel('Duration (mins)')
    ax.set_ylabel('Views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex))
    st.pyplot(fig)

with row10_2:
    
    st.subheader('Histogram of Duration')
    
    fig = Figure()
    ax = fig.subplots()
    sns.histplot(x='duration_mins',data =df, bins=30 ,hue='channelTitle', palette="mako",kde=True, ax=ax)
    ax.set_xlabel('Duration (mins)')
    ax.set_ylabel('Count')
    st.pyplot(fig)

# ---- Row 10a ----

row10a_space1, row10a_1, row10a_space2, row10a_2, row10a_space3 = st.columns((.1, 1, .1, 1, .1))

with row10a_1:
   
    st.subheader('WeekDay vs Views Scatter Plot')
    
    fig = Figure()
    ax = fig.subplots()
    sns.scatterplot(x='weekday', y='viewCount',data =df.sort_values('day_of_week', ascending=True) , palette="magma",hue='caption', ax=ax)
    ax.set_xlabel('Day of Week')
    ax.set_ylabel('Views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

with row10a_2:
    
    st.subheader('Tags vs Views Scatter Plot')
    
    fig = Figure()
    ax = fig.subplots()
    sns.scatterplot(x='tags_count', y='viewCount',data =df , palette="flare",hue='weekday', ax=ax)
    ax.set_xlabel('Tag Count')
    ax.set_ylabel('Views')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos:'{:,.0f}'.format(x/a) + ex ))
    st.pyplot(fig)

# ---- Row 11 ----

row11_space1, row11_1, row11_space2, row11_2, row11_space3 = st.columns((.1, 1, .1, 1, .1))

with row11_1:
    st.subheader('Word Cloud of Title')
    
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
    df['title_no_stopwords'] = df['title'].apply(lambda x: [item for item in str(x).split() if item not in stop_words])

    all_words = list([a for b in df['title_no_stopwords'].tolist() for a in b])
    all_words_str = ' '.join(all_words) 

    def plot_cloud(wordcloud):
        plt.figure(figsize=(30, 20))
        plt.imshow(wordcloud) 
        plt.axis("off");
    
    wordcloud = WordCloud(width = 2000, height = 1000, random_state=1, background_color='black', 
                        colormap='viridis', collocations=False).generate(all_words_str)
    
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.pyplot(plot_cloud(wordcloud))

with row11_2:
    
    nltk.download('stopwords')
    st.subheader('Word Cloud of Tags')
    df['tags_no_stopwords'] = df['tags'].apply(lambda x: [item for item in str(x).split() if item not in stop_words])

    all_words = list([a for b in df['tags_no_stopwords'].tolist() for a in b])
    all_words_str = ' '.join(all_words) 

    def plot_cloud(wordcloud):
        plt.figure(figsize=(30, 20))
        plt.imshow(wordcloud) 
        plt.axis("off");
    
    wordcloud = WordCloud(width = 2000, height = 1000, random_state=1, background_color='black', 
                        colormap='viridis', collocations=False).generate(all_words_str)
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.pyplot(plot_cloud(wordcloud))
    
    
# ---- Last row ----

lrow_space1, lrow_1, lrow_space2 = st.columns((.1,3.2,.1))

with lrow_1:
    st.markdown('***')
    st.markdown("Thanks for going through this mini-analysis with me! I'd love to hear your feedback on this, Feel free to reach out to me on [twitter](https://twitter.com/Mahesh_221)")




