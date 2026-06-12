"""
Rekonstruksi arsitektur NeuMF untuk Lumiere AI.
File .h5 disimpan oleh Keras 3; di Cloud Run kita pakai Keras 2.15 yang tidak
bisa men-deserialisasi InputLayer Keras 3. Solusi: bangun ulang arsitektur lalu
HANYA muat bobotnya (load_weights) -> kebal beda versi Keras.
PENTING: nama layer & dimensi harus sama persis dengan saat training.
"""
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, Embedding, Flatten, Multiply, Concatenate, Dense, Dropout,
)
from tensorflow.keras.regularizers import l2

NUM_USERS = 6040
NUM_MOVIES = 3706
EMBEDDING_SIZE = 32
L2_REG = 1e-4

def build_ncf_model() -> tf.keras.Model:
    user_input = Input(shape=(1,), name="user_input")
    movie_input = Input(shape=(1,), name="movie_input")

    # --- GMF branch ---
    gmf_user = Embedding(NUM_USERS, EMBEDDING_SIZE,
                         embeddings_regularizer=l2(L2_REG),
                         name="gmf_user_embedding")(user_input)
    gmf_user = Flatten()(gmf_user)
    gmf_movie = Embedding(NUM_MOVIES, EMBEDDING_SIZE,
                          embeddings_regularizer=l2(L2_REG),
                          name="gmf_movie_embedding")(movie_input)
    gmf_movie = Flatten()(gmf_movie)
    gmf_product = Multiply(name="gmf_product")([gmf_user, gmf_movie])

    # --- MLP branch ---
    mlp_user = Embedding(NUM_USERS, EMBEDDING_SIZE,
                         embeddings_regularizer=l2(L2_REG),
                         name="mlp_user_embedding")(user_input)
    mlp_user = Flatten()(mlp_user)
    mlp_movie = Embedding(NUM_MOVIES, EMBEDDING_SIZE,
                          embeddings_regularizer=l2(L2_REG),
                          name="mlp_movie_embedding")(movie_input)
    mlp_movie = Flatten()(mlp_movie)
    mlp_vector = Concatenate(name="mlp_concat")([mlp_user, mlp_movie])
    mlp_vector = Dense(64, activation="relu", name="mlp_dense_1")(mlp_vector)
    mlp_vector = Dropout(0.3, name="mlp_dropout_1")(mlp_vector)
    mlp_vector = Dense(32, activation="relu", name="mlp_dense_2")(mlp_vector)
    mlp_vector = Dropout(0.2, name="mlp_dropout_2")(mlp_vector)

    # --- Fusion + output ---
    fusion = Concatenate(name="fusion")([gmf_product, mlp_vector])
    output = Dense(1, activation="sigmoid", name="output")(fusion)

    return Model(inputs=[user_input, movie_input], outputs=output, name="NeuMF")

def load_ncf_model(weights_path: str) -> tf.keras.Model:
    model = build_ncf_model()
    try:
        model.load_weights(weights_path)  # topological (arsitektur identik)
        print("=== [LOADER] Bobot dimuat via topological load. ===")
    except Exception as e_topo:
        print(f"=== [LOADER] Topological gagal ({e_topo}); fallback by_name... ===")
        model.load_weights(weights_path, by_name=True, skip_mismatch=True)
        print("=== [LOADER] Bobot dimuat via by_name load. ===")
    _ = model.predict([np.array([0]), np.array([0])], verbose=0)  # warm-up
    return model