import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 定数とデータ取得 ---
G_URL = "https://www.netflix.com/tudum/top10/data/all-weeks-global.tsv"
C_URL = "https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv"

# Globalデータ用の日本語検索アシスト辞書（必要に応じて自由に追加できます）
JP_TO_EN = {
    "サンクチュアリ": "Sanctuary", "アリス": "Alice", "地面師": "Swindlers",
    "忍び": "Ninja", "幽遊白書": "Yu Yu Hakusho", "ゴジラ": "Godzilla",
    "ワンピース": "ONE PIECE", "寄生獣": "Parasyte", "極悪女王": "Queen of Villains",
    "シティーハンター": "City Hunter", "ブラッシュアップライフ": "Rebooting"
}

@st.cache_data
def load_data():
    df_g = pd.read_csv(G_URL, sep='\t')
    df_c = pd.read_csv(C_URL, sep='\t')
    df_g['week'] = pd.to_datetime(df_g['week'])
    df_c['week'] = pd.to_datetime(df_c['week'])
    df_g.columns = df_g.columns.str.strip()
    df_c.columns = df_c.columns.str.strip()
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

dates = st.sidebar.date_input("分析期間", [df['week'].min().date(), df['week'].max().date()])
mode = st.sidebar.radio("表示モード", ["作品検索 ＆ チャート分析", "週間ランキング表示"])

if len(dates) == 2:
    df = df[(df['week'].dt.date >= dates[0]) & (df['week'].dt.date <= dates[1])]

# --- 3. メイン画面 ---
if mode == "作品検索 ＆ チャート分析":
    st.subheader(f"🔎 作品の検索とトレンド分析: {selected_country}")
    
    if is_global:
        st.info("💡 Globalデータは本来英語のみですが、「地面師」「サンクチュアリ」等の代表作は日本語入力でも自動で英語に変換して検索します（対象国をJapanにすると全作品が日本語検索可能です）。")

    # 検索機能
    raw_query = st.text_input("キーワード検索（タイトルの一部を入力）")
    
    # 検索キーワードの変換処理
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
        st.warning("該当する作品が見つかりません。")
    else:
        # 検索結果から選択する（ここで選ぶと下にチャートが出る）
        selected_titles = st.multiselect("分析する作品を選択してください（選択すると下にチャートが表示されます）", filtered_titles)

        if selected_titles:
            st.markdown("---")
            st.markdown("### 📊 分析チャート ＆ 詳細データ")
            
            chart_df = df[df['show_title'].isin(selected_titles)]
            
            # グラフ項目の選択
            metrics = {'順位 (Rank)': 'weekly_rank', '累計TOP10入り週数': 'cumulative_weeks_in_top_10'}
            if is_global:
                metrics.update({'週間視聴数 (Views)': 'weekly_views', '週間視聴時間 (Hours)': 'weekly_hours_viewed', '再生時間': 'runtime'})
            
            metric_ja = st.selectbox("グラフの縦軸を選択", list(metrics.keys()))
            metric_en = metrics[metric_ja]
            
            # チャート描画
            fig = px.line(chart_df, x='week', y=metric_en, color='show_title', markers=True, title=f"{metric_ja} の推移")
            if metric_en == 'weekly_rank':
                fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
            # 詳細データテーブル描画
            st.write("▼ ランクイン履歴（表）")
            cols = ['week', 'show_title', 'weekly_rank', 'category', 'cumulative_weeks_in_top_10']
            if is_global:
                if 'weekly_views' in chart_df.columns: cols.append('weekly_views')
                if 'weekly_hours_viewed' in chart_df.columns: cols.append('weekly_hours_viewed')
                
            display_df = chart_df[cols].sort_values(['show_title', 'week'], ascending=[True, False])
            
            # 列名の日本語化
            rename_dict = {'week': '週', 'show_title': '作品名', 'weekly_rank': '順位', 'category': 'カテゴリ', 'cumulative_weeks_in_top_10': '累計週数', 'weekly_views': '週間視聴数', 'weekly_hours_viewed': '週間視聴時間(H)'}
            st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True, hide_index=True)

elif mode == "週間ランキング表示":
    st.subheader(f"🏆 週間ランキング: {selected_country}")
    latest_week = df['week'].max()
    st.write(f"📅 集計週: {latest_week.date()}")
    
    cat = st.selectbox("カテゴリ", df['category'].dropna().unique())
    rank_df = df[(df['week'] == latest_week) & (df['category'] == cat)].copy()
    
    if not rank_df.empty:
        cols = ['weekly_rank', 'show_title', 'cumulative_weeks_in_top_10']
        if is_global:
            if 'weekly_views' in rank_df.columns: cols.append('weekly_views')
            if 'weekly_hours_viewed' in rank_df.columns: cols.append('weekly_hours_viewed')
            
        display_df = rank_df[cols].sort_values('weekly_rank')
        rename_dict = {'weekly_rank': '順位', 'show_title': '作品名', 'cumulative_weeks_in_top_10': '累計週数', 'weekly_views': '週間視聴数', 'weekly_hours_viewed': '週間視聴時間(H)'}
        st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True, hide_index=True)
    else:
        st.info("この週のデータはありません。")