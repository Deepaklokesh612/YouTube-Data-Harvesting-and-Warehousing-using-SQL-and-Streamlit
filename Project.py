from googleapiclient.discovery import build
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
import mysql.connector
import datetime
import re

# API key connection
def Api_connect():
    Api_Id="AIzaSyAzt9l1S6CLyrc_lKanxnJaoq-lS60J-sI"
    api_service_name="youtube"
    api_version="v3"
    youtube=build(api_service_name,api_version,developerKey=Api_Id)
    return youtube
youtube=Api_connect()

# Connect to MySQL
def connect_mysql():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="youtube_data_harvesting"
        )
        print("Connected to MySQL database")
        return conn
    except Exception as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# Create necessary tables if they don't exist
def create_tables(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_details (
                Channel_Name VARCHAR(255),
                Channel_Id VARCHAR(255) PRIMARY KEY,
                Subscribers INT,
                Total_Views BIGINT,
                Total_Videos INT,
                Channel_Description TEXT,
                Playlist_Id VARCHAR(255)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_details (
                Playlist_Id VARCHAR(255) PRIMARY KEY,
                Title VARCHAR(255),
                Channel_Id VARCHAR(255),
                Channel_Name VARCHAR(255),
                PublishedAt DATETIME,
                Video_Count INT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_details (
                Channel_Name VARCHAR(255),
                Channel_Id VARCHAR(255),
                Video_Id VARCHAR(255) PRIMARY KEY,
                Title VARCHAR(255),
                Tags TEXT,
                Thumbnail VARCHAR(255),
                Description TEXT,
                Published_Date DATETIME,
                Duration TIME,
                Views BIGINT,
                Likes BIGINT,
                Comments BIGINT,
                Favorite_Count INT,
                Definition VARCHAR(255),
                Caption_Status VARCHAR(255)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_details (
                Comment_Id VARCHAR(255) PRIMARY KEY,
                Video_Id VARCHAR(255),
                Comment_Text TEXT,
                Comment_Author VARCHAR(255),
                Comment_Published DATETIME
            )
        """)
        conn.commit()
        print("Tables created or already exist")
    except Exception as e:
        print(f"Error creating tables: {e}")

# Function to insert data into the corresponding table
def insert_data(conn, table_name, data):
    try:
        cursor = conn.cursor()
        if table_name == "channel_details":
            cursor.execute("""
                INSERT INTO channel_details (
                    Channel_Name, Channel_Id, Subscribers, Total_Views, Total_Videos, Channel_Description, Playlist_Id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                Channel_Name=VALUES(Channel_Name), Subscribers=VALUES(Subscribers),
                Total_Views=VALUES(Total_Views), Total_Videos=VALUES(Total_Videos),
                Channel_Description=VALUES(Channel_Description), Playlist_Id=VALUES(Playlist_Id)
            """, (
                data["Channel_Name"], data["Channel_Id"], data["Subscribers"],
                int(data["Total_Views"]), data["Total_Videos"], data["Channel_Description"],
                data["Playlist_Id"]
            ))
        elif table_name == "playlist_details":
            for item in data:
                published_at = datetime.datetime.strptime(item["PublishedAt"], "%Y-%m-%dT%H:%M:%SZ")
                cursor.execute("""
                    INSERT INTO playlist_details (
                        Playlist_Id, Title, Channel_Id, Channel_Name, PublishedAt, Video_Count
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    Title=VALUES(Title), Channel_Id=VALUES(Channel_Id),
                    Channel_Name=VALUES(Channel_Name), PublishedAt=VALUES(PublishedAt),
                    Video_Count=VALUES(Video_Count)
                """, (
                    item["Playlist_Id"], item["Title"], item["Channel_Id"],
                    item["Channel_Name"], published_at, item["Video_Count"]
                ))
        elif table_name == "video_details":
            def parse_duration(duration):
                 match = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', duration)
                 if not match:
                    return None             
                 hours, minutes, seconds = match.groups()
                 hours = int(hours) if hours else 0
                 minutes = int(minutes) if minutes else 0
                 seconds = int(seconds) if seconds else 0       
                 return f"{hours:02}:{minutes:02}:{seconds:02}"  
            for item in data:
                tags = ', '.join(item["Tags"]) if item["Tags"] else None
                if tags and len(tags) > 65535:
                    tags = tags[:65535]  # Truncate if too long
                published_date = datetime.datetime.strptime(item["Published_Date"], "%Y-%m-%dT%H:%M:%SZ")
                duration = parse_duration(item["Duration"])
                cursor.execute("""
                    INSERT INTO video_details (
                        Channel_Name, Channel_Id, Video_Id, Title, Tags, Thumbnail,
                        Description, Published_Date, Duration, Views, Likes, Comments,
                        Favorite_Count, Definition, Caption_Status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    Channel_Name=VALUES(Channel_Name), Title=VALUES(Title),
                    Tags=VALUES(Tags), Thumbnail=VALUES(Thumbnail),
                    Description=VALUES(Description), Published_Date=VALUES(Published_Date),
                    Duration=VALUES(Duration), Views=VALUES(Views), Likes=VALUES(Likes),
                    Comments=VALUES(Comments), Favorite_Count=VALUES(Favorite_Count),
                    Definition=VALUES(Definition), Caption_Status=VALUES(Caption_Status)
                """, (
                    item["Channel_Name"], item["Channel_Id"], item["Video_Id"], item["Title"],
                    tags, item["Thumbnail"], item["Description"], published_date,
                    duration, item["Views"], item["Likes"], item["Comments"],
                    item["Favorite_Count"], item["Definition"], item["Caption_Status"]
                ))  
        elif table_name == "comment_details":
            for item in data:
                comment_published = datetime.datetime.strptime(item["Comment_Published"], "%Y-%m-%dT%H:%M:%SZ")
                cursor.execute("""
                    INSERT INTO comment_details (
                        Comment_Id, Video_Id, Comment_Text, Comment_Author, Comment_Published
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    Comment_Text=VALUES(Comment_Text), Comment_Author=VALUES(Comment_Author),
                    Comment_Published=VALUES(Comment_Published)
                """, (
                    item["Comment_Id"], item["Video_Id"], item["Comment_Text"],
                    item["Comment_Author"], comment_published
                ))
        conn.commit()
        print(f"Data inserted into {table_name} table")
    except Exception as e:
        print(f"Error inserting data into {table_name} table: {e}")

# Function to get channel information
def get_channel_info(channel_id):
    try:
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()
        if 'items' not in response or not response['items']:
            raise ValueError("No channel information found for the given channel ID")
        for i in response['items']:
            data = {
                "Channel_Name": i["snippet"]["title"],
                "Channel_Id": i["id"],
                "Subscribers": int(i['statistics']['subscriberCount']),
                "Total_Views": int(i['statistics']['viewCount']),
                "Total_Videos": int(i['statistics']['videoCount']),
                "Channel_Description": i["snippet"]["description"],
                "Playlist_Id": i["contentDetails"]["relatedPlaylists"]["uploads"]
            }
        return data
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to get video IDs
def get_videos_ids(channel_id):
    video_ids = []
    response = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    Playlist_Id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    next_page_token = None
    while True:
        response1 = youtube.playlistItems().list(
            part='snippet',
            playlistId=Playlist_Id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token = response1.get('nextPageToken')
        if next_page_token is None:
            break
    return video_ids

# Function to get video information
def get_video_info(video_ids):
    video_data = []
    for video_id in video_ids:
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response = request.execute()
        for video in response['items']:
            data = {
                "Channel_Name": video["snippet"]["channelTitle"],
                "Channel_Id": video["snippet"]["channelId"],
                "Video_Id": video["id"],
                "Title": video["snippet"]["title"],
                "Tags": video["snippet"].get("tags", []),
                "Thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                "Description": video["snippet"]["description"],
                "Published_Date": video["snippet"]["publishedAt"],
                "Duration": video["contentDetails"]["duration"],
                "Views": int(video["statistics"].get("viewCount", 0)),
                "Likes": int(video["statistics"].get("likeCount", 0)),
                "Comments": int(video["statistics"].get("commentCount", 0)),
                "Favorite_Count": int(video["statistics"].get("favoriteCount", 0)),
                "Definition": video["contentDetails"]["definition"],
                "Caption_Status": video["contentDetails"]["caption"]
            }
            video_data.append(data)
    return video_data

# Function to get playlist details
def get_playlist_details(channel_id):
    playlists = []
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        channelId=channel_id,
        maxResults=50
    )
    response = request.execute()
    for playlist in response["items"]:
        data = {
            "Playlist_Id": playlist["id"],
            "Title": playlist["snippet"]["title"],
            "Channel_Id": playlist["snippet"]["channelId"],
            "Channel_Name": playlist["snippet"]["channelTitle"],
            "PublishedAt": playlist["snippet"]["publishedAt"],
            "Video_Count": playlist["contentDetails"]["itemCount"]
        }
        playlists.append(data)
    return playlists

# Function to get comment details
def get_comment_info(video_ids):
    comment_data = []
    try:
        for video_id in video_ids:
            next_page_token = None
            while True:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page_token
                )
                response = request.execute()              
                if 'items' not in response:
                    # Comments are disabled for this video, so skip it
                    print(f"Comments are disabled for video with ID: {video_id}")
                    break                
                for item in response["items"]:
                    comment = item["snippet"]["topLevelComment"]
                    data = {
                        "Comment_Id": comment["id"],
                        "Video_Id": video_id,
                        "Comment_Text": comment["snippet"]["textDisplay"],
                        "Comment_Author": comment["snippet"]["authorDisplayName"],
                        "Comment_Published": comment["snippet"]["publishedAt"]
                    }
                    comment_data.append(data)               
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
    except Exception as e:
        print(f"An error occurred: {e}")
    return comment_data

# Function to upload all details to MySQL
def channel_details(channel_id):
    conn = connect_mysql()
    if conn:
        create_tables(conn)
        ch_details = get_channel_info(channel_id)
        pl_details = get_playlist_details(channel_id)
        vi_ids = get_videos_ids(channel_id)
        vi_details = get_video_info(vi_ids)
        com_details = get_comment_info(vi_ids)
        if ch_details:
            insert_data(conn, "channel_details", ch_details)
        if pl_details:
            insert_data(conn, "playlist_details", pl_details)
        if vi_details:
            insert_data(conn, "video_details", vi_details)
        if com_details:
            insert_data(conn, "comment_details", com_details)
        conn.close()
        return "Upload completed successfully"
    else:
        return "Error connecting to MySQL database"

def tables(channel_name):
    news= channels_table(channel_name)
    if news:
        st.write(news)
    else:
        playlist_table(channel_name)
        videos_table(channel_name)
        comments_table(channel_name)
    return "Tables Created Successfully"

def show_channels_table(conn):
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM channel_details")
        ch_list = cursor.fetchall()        
        if ch_list:
            df = st.dataframe(ch_list)
        else:
            st.write("No data found in channel_details table.")        
        return df
    except Exception as e:
        st.write(f"Error fetching data from channel_details table: {e}")
        return None

def show_playlists_table(conn):
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM playlist_details")
        pl_list = cursor.fetchall()        
        if pl_list:
            df1 = st.dataframe(pl_list)
        else:
            st.write("No data found in playlist_details table.")        
        return df1
    except Exception as e:
        st.write(f"Error fetching data from playlist_details table: {e}")
        return None

def show_videos_table(conn):
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM video_details")
        vi_list = cursor.fetchall()        
        if vi_list:
            df2 = st.dataframe(vi_list)
        else:
            st.write("No data found in video_details table.")        
        return df2
    except Exception as e:
        st.write(f"Error fetching data from video_details table: {e}")
        return None

def show_comments_table(conn):
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM comment_details")
        com_list = cursor.fetchall()        
        if com_list:
            df3 = st.dataframe(com_list)
        else:
            st.write("No data found in comment_details table.")        
        return df3
    except Exception as e:
        st.write(f"Error fetching data from comment_details table: {e}")
        return None

# Function to check if the channel ID already exists in MySQL
def check_channel_exists(conn, channel_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Channel_Id FROM channel_details WHERE Channel_Id = %s", (channel_id,))
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking channel existence: {e}")
        return False

# Function to insert channel details into MySQL
def insert_channel_details(conn, channel_id):
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channel_details (Channel_Id) VALUES (%s)", (channel_id,))
        conn.commit()
        return "Channel details inserted successfully"
    except Exception as e:
        print(f"Error inserting channel details: {e}")
        return "Error: Failed to insert channel details"

# Fetch the Channel Details
def fetch_channel_details(channel_id):
    try:
        request = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        )
        response = request.execute()

        if 'items' not in response or not response['items']:
            raise ValueError("No channel information found for the given channel ID")

        channel_info = response['items'][0]
        channel_details = {
            "Channel_Logo": channel_info["snippet"]["thumbnails"]["high"]["url"],
            "Channel_Name": channel_info["snippet"]["title"],
            "Description": channel_info["snippet"]["description"],
            "Subscribers": int(channel_info['statistics']['subscriberCount']),
            "Total_Videos": int(channel_info['statistics']['videoCount'])
        }
        return channel_details
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Display Channel Details
def display_channel_details(channel_details):
    if "Channel_Logo" in channel_details:
        st.image(channel_details["Channel_Logo"], width=100)
    st.write(f"**Channel Name:** {channel_details['Channel_Name']}")
    st.write(f"**Description:** {channel_details.get('Channel_Description', 'N/A')}")
    st.write(f"**Subscribers Count:** {channel_details.get('Subscribers', 'N/A')}")
    st.write(f"**Total Videos:** {channel_details.get('Total_Videos', 'N/A')}")

# setting up streamlit sidebar menu with options
with st.sidebar:
    st.image("D:\Downloads\Color-YouTube-logo.jpg", use_column_width=True)
    selected = option_menu("Main Menu",
                           ["Home", "Data collection and upload", "MYSQL Database", "Analysis using SQL"],
                           icons=["house", "cloud-upload", "database", "filetype-sql", "bar-chart-line"],
                           menu_icon="menu-up",
                           orientation="vertical")

# Setting up the option "Home" in streamlit page
if selected == "Home":
    st.title(':red[You Tube Data Harvesting & Warehousing using SQL]')
    st.subheader(':blue[Overview :]')
    st.markdown('''Build a simple dashboard or UI using Streamlit and 
                retrieve YouTube channel data with the help of the YouTube API.
                Stored the data in an SQL database (warehousing) managed by XAMPP control panel,
                enabling querying of the data using SQL. Visualize the data within the Streamlit app to uncover insights,
                trends with the YouTube channel data''')
    st.subheader(':blue[Skill Take Away :]')
    st.markdown(''' 
    * Python scripting
    * Data Collection
    * API integration
    * Data Management using SQL
    * Streamlit
    ''')

# Data collection and upload on menu option
if selected == "Data collection and upload":
    st.subheader(':blue[Data collection and upload]')
    st.markdown('''
                - Provide channel ID in the input field.
                - Clicking the 'Show Channel Details' button will display an overview of youtube channel.
                - Clicking 'Collecting and Store Data' will store the extracted channel information,
                Playlists,Videos,Comments in MYSQL Database''')
    st.markdown('''
                :red[note:] ***you can get the channel ID :***
                open youtube - go to any channel - go to about - share cahnnel - copy the channel ID''')    
    channel_id = st.text_input("**Enter the channel ID**")    
    if st.button("Show Channel Details"):
        channel_details = get_channel_info(channel_id)
        if channel_details:
            display_channel_details(channel_details)
        else:
            st.error("Failed to fetch channel details")
    if st.button("Collect and Store Data"):
        with st.spinner('Upload in progress...'):            
            conn = connect_mysql()
            if conn:
                if check_channel_exists(conn, channel_id):
                    st.success("Channel details for the given channel ID already exist")
                else:
                    result = channel_details(channel_id)  # This function will insert all channel details
                    st.success(result)
                    conn.close()
            else:
                st.error("Failed to connect to MySQL database")

# Function to retrieve all channel names from MySQL
def get_all_channels(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Channel_Name FROM channel_details")
        channels = cursor.fetchall()
        return [channel[0] for channel in channels]
    except Exception as e:
        print(f"Error retrieving channels: {e}")
        return []

# To show selected table
if selected == "MYSQL Database":
    conn = connect_mysql()
    if conn:
        all_channels = get_all_channels(conn)
        unique_channel = st.selectbox("List of collected and stored Channels", all_channels)
        show_table = st.radio("**Select the TABLE to view**", ("CHANNELS", "PLAYLISTS", "VIDEOS", "COMMENTS"))
        if show_table == "CHANNELS":
            show_channels_table(conn)
        elif show_table == "PLAYLISTS":
            show_playlists_table(conn)
        elif show_table == "VIDEOS":
            show_videos_table(conn)
        elif show_table == "COMMENTS":
            show_comments_table(conn)
        conn.close()

# Function to execute SQL queries and return results as dataframe
def execute_query(conn, query):
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        if result:
            df = pd.DataFrame(result)
            return df
        else:
            return None
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return None

# SQL queries
queries = {
    "1 : What are the names of all the videos and their corresponding channels?": "SELECT Title AS Video_Name, Channel_Name FROM video_details",
    "2 : Which channels have the most number of videos, and how many videos do they have?": "SELECT Channel_Name, COUNT(*) AS Video_Count FROM video_details GROUP BY Channel_Name ORDER BY Video_Count DESC LIMIT 5",
    "3 : What are the top 10 most viewed videos and their respective channels?": "SELECT Title AS Video_Name, Channel_Name, Views FROM video_details ORDER BY Views DESC LIMIT 10",
    "4 : How many comments were made on each video, and what are their corresponding video names?": "SELECT v.Title AS Video_Name, COUNT(c.Comment_Id) AS Comment_Count FROM video_details v LEFT JOIN comment_details c ON v.Video_Id = c.Video_Id GROUP BY v.Title",
    "5 : Which videos have the highest number of likes, and what are their corresponding channel names?": "SELECT Title AS Video_Name, Channel_Name, Likes FROM video_details ORDER BY Likes DESC LIMIT 10",
    "6 : What is the total number of likes and dislikes for each video, and what are their corresponding video names?": "SELECT Title AS Video_Name, SUM(Likes) AS Total_Likes FROM video_details GROUP BY Title",
    "7 : What is the total number of views for each channel, and what are their corresponding channel names?": "SELECT Channel_Name, SUM(Views) AS Total_Views FROM video_details GROUP BY Channel_Name",
    "8 : What are the names of all the channels that have published videos in the year 2022?": "SELECT DISTINCT Channel_Name FROM video_details WHERE YEAR(Published_Date) = 2022",
    "9 : What is the average duration of all videos in each channel, and what are their corresponding channel names?": "SELECT Channel_Name AS ChannelName,SEC_TO_TIME(AVG(TIME_TO_SEC(Duration))) AS AverageDuration FROM video_details GROUP BY Channel_Name;",
    "10 : Which videos have the highest number of comments, and what are their corresponding channel names?": "SELECT v.Title AS Video_Name,v.Channel_Name,COUNT(c.Comment_Id) AS Comment_Count FROM video_details v LEFT JOIN comment_details c ON v.Video_Id = c.Video_Id GROUP BY v.Video_Id, v.Title, v.Channel_Name ORDER BY Comment_Count DESC LIMIT 10;"}

# Analyzing using SQL on menu option
if selected == 'Analysis using SQL':
    st.subheader(':blue[Analysis using SQL]')
    st.markdown('''You can analyze the collection of YouTube channel data stored in a MySQL database.
                Based on selecting the listed questions below, the output will be displayed in a table format''')
    selected_query = st.radio("Select the SQL query", list(queries.keys()))   
    if st.button("Run Query"):
        conn = connect_mysql()
        if conn:
            df = execute_query(conn, queries[selected_query])
            if df is not None:
                st.write(df)
            else:
                st.write("No results found.")
            conn.close()
        else:
            st.write("Failed to connect to MySQL database.")    
        



    
   
