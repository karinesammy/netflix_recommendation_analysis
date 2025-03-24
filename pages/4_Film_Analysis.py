import streamlit as st
import pandas as pd
import plotly.express as px
import ast
import os

#%% Data Processing
# read netflix data
df = pd.read_csv("\netflix_data_cleaned.csv")

# extract unique type for dropdown menu
show_type = df['type'].dropna().unique()

# extract unique genre for dropdown menu
genres = df['genres'].apply(lambda genre: [i.strip() for i in genre.strip("[]").replace("'", "").split(',') if i.strip() != '']).explode()
genres = sorted(genres.dropna().unique())

# extract unique production_country for dropdown menu
countries = df['country'].apply(lambda country: [i.strip() for i in country.strip("[]").replace("'", "").split(',') if i.strip() != '']).explode()
countries = sorted(countries.dropna().unique())

# extract unique netflix_owned for dropdown menu
netflix_owned = df["netflix_owned"].dropna().unique()


#%% Page setting
st.set_page_config(
    layout="wide",
    page_title="Film Analysis",
    page_icon="📊",
)

#%% Page title
st.title("📊 Film Analysis")

#%% Streamlit - Film Analysis Page
def page_1():

    # Sidebar section for filters
    select_year_range = st.sidebar.slider(
        "Release Year:",
        min_value=int(df['release_year'].min()),  # min year
        max_value=int(df['release_year'].max()),  # max year
        value=(int(df['release_year'].min()), int(df['release_year'].max())), 
        step=1
    )

    select_show_type = st.sidebar.selectbox("Show Type:", show_type)
    select_film_genre = st.sidebar.multiselect("Film Genres:", genres)
    select_netflix_film = st.sidebar.multiselect("Netflix Film:", netflix_owned)
    select_country = st.sidebar.multiselect("Production Countries:", countries)

    # Apply filters to the dataframe
    filtered_df = df[
        (df['release_year'] >= select_year_range[0]) & 
        (df['release_year'] <= select_year_range[1])
    ]

    if select_show_type:
        filtered_df = filtered_df[filtered_df['type'] == select_show_type]

    if select_netflix_film:
        filtered_df = filtered_df[filtered_df['netflix_owned'].isin(select_netflix_film)]

    filtered_df = filtered_df.copy() 
    filtered_df['genres'] = filtered_df['genres'].apply(lambda x: [i.strip() for i in x.strip("[]").replace("'", "").split(',')])
    filtered_df = filtered_df.explode('genres')

    if select_film_genre:
        filtered_df = filtered_df[filtered_df['genres'].isin(select_film_genre)]

    filtered_df['country'] = filtered_df['country'].apply(lambda x: [i.strip() for i in x.strip("[]").replace("'", "").split(',')])
    filtered_df = filtered_df.explode('country')

    if select_country:
        filtered_df = filtered_df[filtered_df['country'].isin(select_country)]


    # Calculation:
    filtered_df['decade'] = (filtered_df['release_year'] // 10) * 10
    production_netflix = (filtered_df.groupby(['decade', 'netflix_owned']).size().reset_index(name='Count')) # production counts of Netflix vs. Non-Netflix
    production_genre = (filtered_df.groupby(['decade', 'genres']).size().unstack(fill_value=0).reset_index()) # group by decade and genre

    # Reshape from wide to long format
    df_long = production_genre.melt(
        id_vars='decade',
        var_name='Genre',
        value_name='Count'
    )

    # Calculation: total count if no genre is selected
    if not select_film_genre:
        df_long = df_long.groupby("decade", as_index=False)["Count"].sum()
        df_long["Genre"] = "Total Count"

    # Chart 1: Production Trend: Netflix vs. Non-Netflix
    fig_netflix_trend = px.line(
        production_netflix,
        x='decade',
        y='Count',
        color='netflix_owned',
        markers=True,
        title="Production Trend: Netflix vs. Non-Netflix",
        labels={"decade": "Release Year", "Count": "Number of Productions", "netflix_owned": "Netflix Owned"}
    )

    # Chart 2: Production Trend: by Genres
    fig_genre_trend = px.line(
        df_long,
        x='decade',
        y='Count',
        color='Genre',
        markers=True,
        title="Production Trend: by Genres",
        subtitle="*Select at least 2 genres to view comparison.",
        labels={
            "decade": "Release Year",
            "Count": "Number of Productions",
            "Genre": "Genre"
        }
    )

    # Chart 3: Production Trend: by Genres and Countries
    production_genre_country = (filtered_df.groupby(['decade', 'genres', 'country']).size().reset_index(name='Count'))
    production_genre_country_sorted = production_genre_country.sort_values(by='Count', ascending=False)

    fig_genre_country_trend = px.bar(
        production_genre_country_sorted,
        x="Count",
        y="genres",
        color="country", 
        orientation="h",
        title="Production Trend: by Genres and Countries",
        labels={
            "genres": "Genre",
            "Count": "Number of Productions",
            "country": "Country"
        },
        barmode="stack", 
        category_orders={
            "genres": production_genre_country_sorted.groupby("genres")['Count'].sum().sort_values(ascending=False).index.tolist()
        }
    )

    fig_genre_country_trend.update_layout(
        height=750,
        margin=dict(l=200)
    )

    # Display charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(fig_netflix_trend, use_container_width=True)
    with col2:
        st.plotly_chart(fig_genre_trend, use_container_width=True)

    st.plotly_chart(fig_genre_country_trend, use_container_width=True)


#%% Streamlit - Film Analysis Page
def page_2():
    # 1. Explode 'genres' so each genre is a separate row (ensure 'genres' is a list of genres before exploding)
    df_exploded = df.copy()  # Create a copy to work on
    df_exploded['genres'] = df_exploded['genres'].apply(lambda x: x.strip("[]").replace("'", "").split(',') if isinstance(x, str) else x)  # Clean the 'genres' list
    df_exploded = df_exploded.explode('genres').copy()  # Now explode the list into separate rows
    
    # 2. Remove rows where 'genres' is NaN or empty
    df_exploded = df_exploded[df_exploded['genres'].notna() & (df_exploded['genres'] != '')]
    
    # 3. Calculate overall average IMDb score for each genre
    overall_scores = df_exploded.groupby('genres')['imdb_score'].mean().sort_values(ascending=False)
    
    # 4. Calculate Netflix-owned average IMDb score for each genre
    netflix_scores = df_exploded[df_exploded['netflix_owned'] == True].groupby('genres')['imdb_score'].mean()
    
    # 5. Calculate Non-Netflix average IMDb score for each genre
    non_netflix_scores = df_exploded[df_exploded['netflix_owned'] == False].groupby('genres')['imdb_score'].mean()
    
    # 6. Pick top 10 genres by overall average score
    top10_genres = overall_scores.head(10).index
    
    # 7. Build a DataFrame to compare Netflix vs. Non-Netflix
    df_compare = pd.DataFrame({'genres': top10_genres})
    df_compare['Netflix'] = df_compare['genres'].map(netflix_scores).fillna(0)
    df_compare['Non-Netflix'] = df_compare['genres'].map(non_netflix_scores).fillna(0)
    
    # 8. Melt the DataFrame to long form for a grouped bar chart
    df_melt = df_compare.melt(
        id_vars='genres',
        var_name='Ownership',
        value_name='imdb_score'
    )
    
    # 9. Create a grouped bar chart
    fig = px.bar(
        df_melt,
        x='genres',
        y='imdb_score',
        color='Ownership',
        barmode='group',
        text='imdb_score',
        title="Top 10 Genres with the Highest IMDb Scores",
        labels={
            'genres': 'Genres',
            'imdb_score': 'Avg. IMDb Score',
            'Ownership': 'Category'
        }
    )
    
    fig.update_traces(
        textposition='outside',
        texttemplate='%{text:.2f}'
    )
    
    fig.update_layout(
    yaxis=dict(tickmode='linear', dtick=0.1, range=[6, 7.5]),
    autosize=False,
    width=1000,
    height=600,
    showlegend=True,  # Ensure the legend is shown
    legend_title=None,  # Hide the legend title
)

    
    st.plotly_chart(fig, use_container_width=False)



def page_3():
    
    # 1. Explode 'genres' so each genre is a separate row
    df_exploded = df.copy()  # Make a copy of the original dataframe
    df_exploded['genres'] = df_exploded['genres'].apply(lambda x: x.strip("[]").replace("'", "").split(',') if isinstance(x, str) else x)  # Clean the 'genres' list
    df_exploded = df_exploded.explode('genres').copy()  # Now explode the list into separate rows
    
    # 2. Remove rows where 'genres' is NaN or empty
    df_exploded = df_exploded[df_exploded['genres'].notna() & (df_exploded['genres'] != '')]
    
    # 3. Calculate overall total IMDb votes for each genre
    overall_votes = df_exploded.groupby('genres')['imdb_votes'].sum().sort_values(ascending=False)
    
    # 4. Calculate Netflix-owned total IMDb votes for each genre
    netflix_votes = df_exploded[df_exploded['netflix_owned'] == True].groupby('genres')['imdb_votes'].sum()
    
    # 5. Calculate Non-Netflix total IMDb votes for each genre
    non_netflix_votes = df_exploded[df_exploded['netflix_owned'] == False].groupby('genres')['imdb_votes'].sum()
    
    # 6. Identify the top 10 genres by overall total votes
    top10_genres = overall_votes.head(10).index
    
    # 7. Build a DataFrame to compare Netflix vs. Non-Netflix
    df_compare = pd.DataFrame({'genres': top10_genres})
    df_compare['Netflix'] = df_compare['genres'].map(netflix_votes).fillna(0)
    df_compare['Non-Netflix'] = df_compare['genres'].map(non_netflix_votes).fillna(0)
    
    # 8. Melt the DataFrame to long form for a grouped bar chart
    df_melt = df_compare.melt(
        id_vars='genres',
        var_name='Category',
        value_name='imdb_votes'
    )
    
    # 9. Create a grouped bar chart
    fig = px.bar(
        df_melt,
        x='genres',
        y='imdb_votes',
        color='Category',
        barmode='group',
        text='imdb_votes',
        title="Top 10 Genres with the Highest Total IMDb Votes",
        labels={
            'genres': 'Genre',
            'imdb_votes': 'Total IMDb Votes',
            'Category': 'Ownership'
        }
    )
    
    # 10. Format labels with commas, position outside, and increase font size
    fig.update_traces(
        textposition='outside',
        texttemplate='%{text:,.0f}'
    )
    
    # 11. Adjust layout for readability
    fig.update_layout(
        autosize=False,
        width=1300,
        height=600,
        legend_title=None  # Hide legend title
    )
    
    st.plotly_chart(fig, use_container_width=True)



def page_4():

    # 1. SIDEBAR SECTION
    min_year = int(df['release_year'].min())
    max_year = int(df['release_year'].max())
    year_range = st.sidebar.slider(
        "Select Release Year Range:",
        min_value=min_year,
        max_value=max_year,
        value=(2000, 2022),
        step=1
    )

    type_options = sorted(df['type'].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect(
        "Select Type:",
        options=type_options,
        default=type_options
    )

    netflix_options = [True, False]
    selected_netflix = st.sidebar.multiselect(
        "Netflix Owned",
        options=netflix_options,
        default=netflix_options
    )

    if not selected_netflix:
        st.warning("Please select at least one option for 'Netflix Owned' to proceed.")
        st.stop()

    
    # 2. FILTER DATA
    df_plot = df[
        (df['release_year'] >= year_range[0]) &
        (df['release_year'] <= year_range[1]) &
        (df['type'].isin(selected_types)) &
        (df['netflix_owned'].isin(selected_netflix))
    ].dropna(subset=["runtime", "imdb_score"])


    # 3. (Optional) CORRELATION CALC
    # Even if we remove the line, we can still compute correlation for reference if desired.
    # If you don't want the correlation at all, remove this block.
    if len(df_plot) > 1:
        correlation = df_plot["runtime"].corr(df_plot["imdb_score"])
    else:
        correlation = 0.0

    # 4. CREATE SCATTER + HISTOGRAM
    # Removed 'trendline="ols"' and 'trendline_scope="overall"'
    fig = px.scatter(
        df_plot,
        x="runtime",
        y="imdb_score",
        color="type",
        hover_data=["title", "genres"],
        marginal_x="histogram",  # Adds a histogram on top
        title=(f"{year_range[0]}–{year_range[1]} Runtime vs. IMDb Scores (Correlation: {correlation:.2f})"),
        labels={
            "runtime": "Runtime (minutes)",
            "imdb_score": "IMDb Score",
            "type": "Type"
        }
    )


    # 5. DISABLE HISTOGRAM NORMALIZATION
    for trace in fig.data:
        if trace.type == "histogram":
            trace.histnorm = None  # raw counts instead of density/percent

    # 6. DECOUPLE SUBPLOTS & LABEL
    fig.update_layout(
        autosize=False,
        width=1000,
        height=700,
        xaxis=dict(tickfont=dict(size=12)),
        yaxis=dict(tickfont=dict(size=12)),
        xaxis2=dict(matches=None),
        yaxis2=dict(matches=None),
        legend_title=None
    )

    if "yaxis2" in fig.layout:
        fig.layout.yaxis2.title = "Count of Films"
        fig.layout.yaxis2.showgrid = True
        fig.layout.yaxis2.tickmode = "auto"

    # 7. DISPLAY THE CHART
    st.plotly_chart(fig, use_container_width=False)


#%% Streamlit - Define PAGES
PAGES = {
    "Production Trend": page_1,
    "Top 10 Genres with the Highest IMDb Scores": page_2,
    "Top 10 Genres with the Highest Total IMDb Votes": page_3,
    "Runtime vs. IMDb Scores": page_4
}

#%% Streamlit - select page
page = st.sidebar.selectbox("Select a page:", options=list(PAGES.keys()))

# Page switch
PAGES[page]()
