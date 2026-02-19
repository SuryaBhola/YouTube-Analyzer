import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from googleapiclient.discovery import build
from collections import Counter
import re
from datetime import datetime
import io

# --- 1. CORE ANALYTICS ENGINES (DO NOT CHANGE) ---
def extract_video_id(url):
    pattern = r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_youtube_data(api_key, video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(part="snippet,statistics", id=video_id)
        response = request.execute()
        if not response['items']: return None
        item = response['items'][0]
        return {
            "Title": item['snippet']['title'],
            "Description": item['snippet']['description'],
            "PublishedAt": item['snippet']['publishedAt'],
            "ChannelId": item['snippet']['channelId'],
            "ChannelTitle": item['snippet']['channelTitle'],
            "Views": int(item['statistics'].get('viewCount', 0)),
            "Likes": int(item['statistics'].get('likeCount', 0)),
            "Comments": int(item['statistics'].get('commentCount', 0)),
            "Thumbnail": item['snippet']['thumbnails'].get('maxres', item['snippet']['thumbnails'].get('high'))['url']
        }
    except: return None

def get_channel_stats(api_key, channel_id):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.channels().list(part="statistics,snippet", id=channel_id)
        response = request.execute()
        item = response['items'][0]
        total_views = int(item['statistics'].get('viewCount', 0))
        total_videos = int(item['statistics'].get('videoCount', 0))
        
        video_req = youtube.search().list(channelId=channel_id, part="id", order="date", maxResults=10, type="video")
        v_ids = [v['id']['videoId'] for v in video_req.execute()['items']]
        stats_res = youtube.videos().list(id=",".join(v_ids), part="statistics").execute()
        total_recent_likes = sum(int(v['statistics'].get('likeCount', 0)) for v in stats_res['items'])
        
        return {
            "Subscribers": int(item['statistics'].get('subscriberCount', 0)),
            "TotalViews": total_views,
            "TotalVideos": total_videos,
            "AvgViews": total_views // total_videos if total_videos > 0 else 0,
            "AvgLikes": total_recent_likes // len(v_ids) if v_ids else 0,
            "ProfilePic": item['snippet']['thumbnails']['high']['url']
        }
    except: return None

def get_ryd_dislikes(video_id):
    url = f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('dislikes', 0)
    except: pass
    return 0

def get_deep_pulse(api_key, video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        all_comments = []
        next_page_token = None
        for i in range(5): 
            request = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=100, pageToken=next_page_token, textFormat="plainText")
            response = request.execute()
            for item in response['items']:
                all_comments.append(item['snippet']['topLevelComment']['snippet']['textDisplay'])
            next_page_token = response.get('nextPageToken')
            if not next_page_token: break
        words = re.findall(r'\w+', " ".join(all_comments).lower())
        stop_words = {'the', 'this', 'that', 'with', 'from', 'your', 'have', 'very', 'just', 'song', 'video'}
        filtered = [w for w in words if w not in stop_words and len(w) > 3]
        return Counter(filtered).most_common(15), len(all_comments)
    except: return [], 0

# --- 2. $1,000,000 PREMIUM UI DESIGN ---
st.set_page_config(page_title="YouTube Analyzer | Surya Bhola", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp {
        background: radial-gradient(circle at top right, #1a1a2e, #050505);
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(255, 0, 0, 0.05) 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(255, 0, 0, 0.05) 0%, transparent 40%);
        overflow: hidden;
    }

    .stApp::before {
        content: "▶"; font-size: 150px; color: rgba(255, 255, 255, 0.03);
        position: absolute; top: 10%; left: 5%; transform: rotate(-15deg);
        animation: float 8s infinite ease-in-out;
    }

    @keyframes float { 0%, 100% { transform: translateY(0) rotate(-15deg); } 50% { transform: translateY(-40px) rotate(-10deg); } }

    .login-container {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 60px 50px; border-radius: 40px; background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(30px); border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 50px 100px rgba(0,0,0,0.8); margin: auto; margin-top: 50px; max-width: 700px;
    }

    .hero-title { 
        font-size: 68px; font-weight: 800; letter-spacing: -2px; line-height: 1;
        background: linear-gradient(135deg, #00ff88 0%, #00bdff 50%, #ff0055 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px);
        border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 30px; margin-bottom: 25px; box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.02); border-radius: 20px; padding: 20px;
        border-left: 5px solid #00ff88; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    .signature-main { 
        position: fixed; bottom: 30px; right: 40px; font-family: 'Brush Script MT', cursive; 
        font-size: 32px; color: rgba(0, 255, 136, 0.8); pointer-events: none; z-index: 1000;
    }
    </style>
    <div class="signature-main">Surya Bhola</div>
""", unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False

# --- 3. RE-IMAGINED HOME PAGE (Option B Integrated) ---
if not st.session_state.auth:
    _, col_mid, _ = st.columns([1, 4, 1])
    with col_mid:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 50px; margin-bottom: 20px;'>⚡</div>", unsafe_allow_html=True)
        st.markdown("<h1 class='hero-title'>YouTube Analyzer</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: rgba(255,255,255,0.5); letter-spacing: 5px; text-transform: uppercase;'>High-Performance Intelligence</p>", unsafe_allow_html=True)
        
        # User can enter their own key, or leave blank to use the Guest Key
        u_key = st.text_input("YouTube API Key", type="password", placeholder="Leave blank for Guest Mode...")
        u_url = st.text_input("Target Video URL", placeholder="https://www.youtube.com/watch?v=...")
        
        if st.button("INITIALIZE ANALYSIS ENGINE"):
            # Option B Logic: Use secrets if input is blank
            final_key = u_key if u_key else st.secrets.get("YOUTUBE_API_KEY")
            
            if final_key and extract_video_id(u_url):
                st.session_state.key, st.session_state.url, st.session_state.auth = final_key, u_url, True
                st.rerun()
            elif not final_key:
                st.error("Missing API Configuration. Please enter a key or contact Surya.")
            else:
                st.error("Invalid URL format detected.")

        st.markdown("<p style='color: #00ff88; font-weight: 800; margin-top: 30px;'>Designed & Coded by Surya Bhola</p></div>", unsafe_allow_html=True)

# --- 4. MASTER INNER DASHBOARD ---
else:
    v_id = extract_video_id(st.session_state.url)
    data = get_youtube_data(st.session_state.key, v_id)
    if data:
        if st.sidebar.button("🚪 TERMINATE SESSION"):
            st.session_state.auth = False
            st.rerun()

        st.markdown(f"<h1 style='font-size: 42px; font-weight: 800;'>📊 {data['Title']}</h1>", unsafe_allow_html=True)
        tab_v, tab_c = st.tabs(["🎥 Video Intelligence", "🏢 Creator Insights"])
        
        with tab_v:
            dislikes = get_ryd_dislikes(v_id)
            pulse, count = get_deep_pulse(st.session_state.key, v_id)
            eng_rate = round(((data['Likes'] + data['Comments']) / data['Views']) * 100, 2)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👁️ TOTAL VIEWS", f"{data['Views']:,}")
            c2.metric("👍 TOTAL LIKES", f"{data['Likes']:,}")
            c3.metric("👎 TOTAL DISLIKES", f"{dislikes:,}")
            c4.metric("💬 TOTAL COMMENTS", f"{data['Comments']:,}")

            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            m1, m2 = st.columns([2, 1])
            with m1: st.video(st.session_state.url)
            with m2:
                st.image(data['Thumbnail'], use_container_width=True)
                st.download_button("🖼️ EXPORT THUMBNAIL", requests.get(data['Thumbnail']).content, f"{v_id}.jpg")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("📈 Interaction Velocity & Sentiment")
            ch1, ch2 = st.columns([1, 1.5])
            with ch1:
                fig_g = go.Figure(go.Indicator(mode="gauge+number", value=eng_rate,
                    title={'text': "Engagement Velocity %"},
                    gauge={'axis': {'range': [0, 20]}, 'bar': {'color': "#00ff88"},
                           'steps': [{'range': [0, 5], 'color': 'rgba(255, 75, 75, 0.2)'}, {'range': [12, 20], 'color': 'rgba(0, 255, 136, 0.2)'}]}))
                fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", height=300)
                st.plotly_chart(fig_g, use_container_width=True)
            with ch2:
                fig_p = px.pie(values=[data['Likes'], dislikes], names=["Likes", "Dislikes"], hole=0.7, color_discrete_sequence=['#00ff88', '#ff4b4b'])
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("📝 Audience Pulse Map")
            if pulse:
                p_df = pd.DataFrame(pulse, columns=['Keyword', 'Count']).sort_values(by='Count')
                fig_bar = px.bar(p_df, x='Count', y='Keyword', orientation='h', color='Count', color_continuous_scale='Greens')
                fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_c:
            chan = get_channel_stats(st.session_state.key, data['ChannelId'])
            if chan:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.subheader(f"🏢 Profile: {data['ChannelTitle']}")
                col_pic, col_info = st.columns([1, 4])
                with col_pic:
                    st.image(chan['ProfilePic'], use_container_width=True)
                    st.download_button("📥 DOWNLOAD PIC", requests.get(chan['ProfilePic']).content, "profile.jpg")
                with col_info:
                    cc1, cc2, cc3 = st.columns(3)
                    cc1.metric("SUBSCRIBERS", f"{chan['Subscribers']:,}")
                    cc2.metric("TOTAL VIEWS", f"{chan['TotalViews']:,}")
                    cc3.metric("TOTAL VIDEOS", f"{chan['TotalVideos']:,}")
                    ca1, ca2 = st.columns(2)
                    ca1.metric("AVG VIEWS/VIDEO", f"{chan['AvgViews']:,}")
                    ca2.metric("AVG LIKES/VIDEO", f"{chan['AvgLikes']:,}")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.subheader("🎯 Subscriber Milestones")
                next_goal = 10**len(str(chan['Subscribers'])) if chan['Subscribers'] < 10**len(str(chan['Subscribers'])) else chan['Subscribers'] * 2
                remaining = next_goal - chan['Subscribers']
                st.write(f"This creator is **{remaining:,}** subs away from **{next_goal:,}**!")
                st.progress(chan['Subscribers'] / next_goal)
                st.markdown("</div>", unsafe_allow_html=True)