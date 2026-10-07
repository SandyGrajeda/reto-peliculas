import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from sqlalchemy import create_engine, text


st.set_page_config(page_title="Películas de Netflix", page_icon="🎬", layout="wide")
st.markdown('<html lang="es" class="notranslate" translate="no"><head><meta name="google" content="notranslate" /></head>', unsafe_allow_html=True)


if not firebase_admin._apps:
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
    else:
        cred = credentials.Certificate("firebase_key.json")
    
    firebase_admin.initialize_app(cred)

db = firestore.client()


if "postgres" in st.secrets:
    pg = st.secrets["postgres"]
    DATABASE_URL = f"postgresql://{pg['username']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}?sslmode=require"
else:
    DATABASE_URL = "postgresql://avnadmin:AVNS_0v9MWg2dhG-JE-r-iLt@guests-db-guests.k.aivencloud.com:22347/defaultdb?sslmode=require"

engine = create_engine(DATABASE_URL)


@st.cache_data
def load_movies_data():
    """Carga los registros de películas desde Firestore."""
    movies_ref = db.collection("movies")
    docs = movies_ref.stream()
    movies_list = [doc.to_dict() for doc in docs]
    return pd.DataFrame(movies_list)


def load_comments_data():
    """Consulta la tabla 'people' en PostgreSQL."""
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT email, comment FROM people"), conn)
    return df


data = load_movies_data()

st.title("Aplicación películas de Netflix")
st.caption("Nota: Para buscar por filtro debes tener deseleccionado 'Mostrar todas las películas'.")


sidebar_checkbox = st.sidebar.checkbox("Mostrar todas las peliculas")
st.sidebar.write("---")

title_search = st.sidebar.text_input("Selecciona la pelicula:")
btn_search_title = st.sidebar.button("Buscar")
st.sidebar.write("---")

directors_list = sorted(data['director'].dropna().unique().tolist()) if not data.empty and 'director' in data.columns else []
selected_director = st.sidebar.selectbox("Selecciona el Director", directors_list)
btn_filter_director = st.sidebar.button("Buscar por director")
st.sidebar.write("---")

st.sidebar.subheader("Nuevo Registro")
new_movie_name = st.sidebar.text_input("Name:")
company_list = sorted(data['company'].dropna().unique().tolist()) if not data.empty and 'company' in data.columns else []
new_movie_company = st.sidebar.selectbox("Company", company_list)
new_movie_director = st.sidebar.selectbox("Director", directors_list)
genre_list = sorted(data['genre'].dropna().unique().tolist()) if not data.empty and 'genre' in data.columns else ["Action", "Comedy", "Drama", "Sci-Fi"]
new_movie_genre = st.sidebar.selectbox("Genre", genre_list)
btn_add_movie = st.sidebar.button("Guardar")

st.sidebar.write("---")

st.sidebar.subheader("Libro de Visitas")
with st.sidebar.form(key="guestbook_form", clear_on_submit=True):
    visitor_email = st.text_input("Correo electrónico:")
    visitor_comment = st.text_area("Comentario:")
    btn_submit_guest = st.form_submit_button("Enviar comentario")

if btn_submit_guest:
    if visitor_email.strip() != "" and visitor_comment.strip() != "":
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO people (email, comment) VALUES (:email, :comment)"),
                {"email": visitor_email, "comment": visitor_comment}
            )
        st.sidebar.success("¡Gracias por tu comentario!")
    else:
        st.sidebar.error("Completa tu correo y comentario.")

btn_view_comments = st.sidebar.button("Ver comentarios de visitantes")

if btn_add_movie:
    if new_movie_name.strip() != "":
        new_doc = {
            "name": new_movie_name,
            "company": new_movie_company,
            "director": new_movie_director,
            "genre": new_movie_genre
        }
        db.collection("movies").add(new_doc)
        st.sidebar.success(f"Película '{new_movie_name}' guardada")
        st.cache_data.clear()
        st.rerun()
    else:
        st.sidebar.error("El nombre de la pelicula no puede estar vacío.")

if sidebar_checkbox:
    st.subheader("Todas las peliculas")
    st.dataframe(data, use_container_width=True)

elif btn_search_title:
    if title_search.strip() != "":
        filtered_df = data[data['name'].str.contains(title_search, case=False, na=False)] if not data.empty else pd.DataFrame()
        st.subheader(f"Total de peliculas mostradas : {len(filtered_df)}")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("Ingresa un título para la búsqueda.")

elif btn_filter_director:
    filtered_df = data[data['director'] == selected_director] if not data.empty else pd.DataFrame()
    st.subheader(f"Total de peliculas : {len(filtered_df)}")
    st.dataframe(filtered_df, use_container_width=True)

elif btn_view_comments:
    st.subheader("Comentarios de Visitantes (PostgreSQL)")
    df_comments = load_comments_data()
    st.dataframe(df_comments, use_container_width=True)