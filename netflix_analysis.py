import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 定数とデータ取得 ---
G_URL = "https://www.netflix.com/tudum/top10/data/all-weeks-global.tsv"
C_URL = "https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv"

JP_TO_EN = {
    "サンクチュアリ": "Sanctuary", "アリス": "Alice", "地面師": "Swindlers",
    "忍び": "Ninja", "幽遊白書": "Yu Yu Hakusho", "ゴジラ": "Godzilla",
    "ワンピース": "ONE PIECE", "寄生獣": "Parasyte", "極悪女王": "Queen of Villains",
    "シティーハンター": "City Hunter", "ブラッシュアップライフ": "Rebooting",
    "ウェンズデー": "Wednesday"
}

@st.cache_data
def load_data():
    df_g = pd.read_csv(G_URL, sep='\t')
    df_c = pd.read_csv(C_URL, sep='\t')
    df_g['week'] = pd.to_datetime(df_g['week'])
    df_c['week'] = pd.to_datetime(df_c['week'])
    df_g.columns = df_g.columns.str.strip()
    df_c.columns = df_c.columns.str.strip()
    
    # 映画などシーズン名が空欄の場合は、作品名で埋める
    df_g['season_title'] = df_g['season_title'].fillna(df_g['show_title'])
    df_c['season_title'] = df_c['season_title'].fillna(df_c['show_title'])
    
    return df_g, df_c

st.set_page_config(page_title="Netflix分析", layout="wide")
st.warning("⚠️ ブラウザの「自動翻訳」がオンだとクラッシュします。オフにしてご利用ください。")
st.title("🎬 Netflix分析ダッシュボード")

try:
    df_global, df_country = load_data()
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# --- 2. サイドバー設定 ---
st.sidebar.header("🔍 分析フィルター")

countries = ["全世界 (Global)"] + sorted(df_country['country_name'].dropna().unique().tolist())
selected_country = st.sidebar.selectbox("分析対象の国", countries)

if selected_country == "全世界 (Global)":
    df = df_global.copy()
    is_global = True
else:
    df = df_country[df_country['country_name'] == selected_country].copy()
    is_global = False

# ★ ここがアップデート部分：開始日と終了日を明確に分離！
st.sidebar.markdown("---")
st.sidebar.markdown("**📅 分析期間の指定**")
min_date_val = df['week'].min().date()
max_date_val = df['week'].max().date()

start_date = st.sidebar.date_input("開始日", min_date_val, min_value=min_date_val, max_value=max_date_val)
end_date = st.sidebar.date_input("終了日", max_date_val, min_value=min_date_val, max_value=max_date_val)

# 開始日と終了日の整合性チェック
if start_date > end_date:
    st.sidebar.error("⚠️ エラー: 開始日は終了日より前の日付を指定してください。")
    # エラー時はデータを空にしてグラフを描画させない
    df = df.iloc[0:0] 
else:
    # 正常な場合は期間でフィルタリング
    df = df[(df['week'].dt.date >= start_date) & (df['week'].dt.date <= end_date)]

st.sidebar.markdown("---")
mode = st.sidebar.radio("表示モード", ["作品検索 ＆ チャート分析", "週間ランキング表示"])

# --- 3. メイン画面 ---
if mode == "作品検索 ＆ チャート分析":
    st.subheader(f"🔎 作品の検索とトレンド分析: {selected_country}")
    
    raw_query = st.text_input("キーワード検索（タイトルの一部を入力）")
    
    search_query = raw_query
    if is_global and raw_query:
        for jp_word, en_word in JP_TO_EN.items():
            if jp_word in raw_query:
                search_query = en_word
                st.toast(f"自動的に「{en_word}」で検索しました！")
                break

    all_titles = sorted(df['show_title'].dropna().unique())
    
    if search_query:
        filtered_titles = [t for t in all_titles if search_query.lower() in t.lower()]
    else:
        filtered_titles = all_titles

    if not filtered_titles:
        st.warning("該当する作品が見つかりません。期間やキーワードを変更してください。")
    else:
        selected_titles = st.multiselect("分析する作品を選択してください", filtered_titles)

        if selected_titles:
            st.markdown("---")
            st.markdown("### 📊 分析チャート ＆ 詳細データ")
            
            chart_df = df[df['show_title'].isin(selected_titles)]
            
            metrics = {'順位 (Rank)': 'weekly_rank', '累計TOP10入り週数': 'cumulative_weeks_in_top_10'}
            if is_global:
                metrics.update({'週間視聴数 (Views)': 'weekly_views', '週間視聴時間 (Hours)': 'weekly_hours_viewed', '再生時間': 'runtime'})
            
            metric_ja = st.selectbox("グラフの縦軸を選択", list(metrics.keys()))
            metric_en = metrics[metric_ja]
            
            fig = px.line(chart_df, x='week', y=metric_en, color='season_title', markers=True, title=f"{metric_ja} の推移 (シーズン別)")
            if metric_en == 'weekly_rank':
                fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("▼ ランクイン履歴（表）")
            cols = ['week', 'show_title', 'season_title', 'weekly_rank', 'category', 'cumulative_weeks_in_top_10']
            if is_global:
                if 'weekly_views' in chart_df.columns: cols.append('weekly_views')
                if 'weekly_hours_viewed' in chart_df.columns: cols.append('weekly_hours_viewed')
                
            display_df = chart_df[cols].sort_values(['show_title', 'season_title', 'week'], ascending=[True, True, False])
            
            rename_dict = {'week': '週', 'show_title': '作品名', 'season_title': 'シーズン名', 'weekly_rank': '順位', 'category': 'カテゴリ', 'cumulative_weeks_in_top_10': '累計週数', 'weekly_views': '週間視聴数', 'weekly_hours_viewed': '週間視聴時間(H)'}
            st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True, hide_index=True)

elif mode == "週間ランキング表示":
    st.subheader(f"🏆 週間ランキング: {selected_country}")
    
    if not df.empty:
        latest_week = df['week'].max()
        st.write(f"📅 集計週: {latest_week.date()}")
        
        cat = st.selectbox("カテゴリ", df['category'].dropna().unique())
        rank_df = df[(df['week'] == latest_week) & (df['category'] == cat)].copy()
        
        if not rank_df.empty:
            cols = ['weekly_rank', 'season_title', 'cumulative_weeks_in_top_10']
            if is_global:
                if 'weekly_views' in rank_df.columns: cols.append('weekly_views')
                if 'weekly_hours_viewed' in rank_df.columns: cols.append('weekly_hours_viewed')
                
            display_df = rank_df[cols].sort_values('weekly_rank')
            rename_dict = {'weekly_rank': '順位', 'season_title': 'シーズン名', 'cumulative_weeks_in_top_10': '累計週数', 'weekly_views': '週間視聴数', 'weekly_hours_viewed': '週間視聴時間(H)'}
            st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True, hide_index=True)
        else:
            st.info("この週のデータはありません。")
    else:
        st.warning("選択された期間にデータがありません。")
