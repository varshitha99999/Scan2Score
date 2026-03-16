"""
Handwritten Digit Recognizer — CNN Model Training
Uses MNIST dataset with a CNN to achieve ~99% accuracy
"""

import numpy as np
import os

# ── TensorFlow / Keras ──────────────────────────────────────────────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"          # suppress TF info logs
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

# ── Sklearn utilities ───────────────────────────────────────────────────────
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib
matplotlib.use("Agg")                              # headless backend
import matplotlib.pyplot as plt
import seaborn as sns


# ═══════════════════════════════════════════════════════════════════════════
# 1. LOAD & PRE-PROCESS DATA
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Download MNIST and prepare train / validation / test splits."""
    (X_train_full, y_train_full), (X_test, y_test) = keras.datasets.mnist.load_data()

    # Normalise pixel values to [0, 1] and add channel dim  → (N, 28, 28, 1)
    X_train_full = X_train_full.astype("float32") / 255.0
    X_test       = X_test.astype("float32") / 255.0

    X_train_full = X_train_full[..., np.newaxis]
    X_test       = X_test[..., np.newaxis]

    # Carve out 10 % of training data for validation
    val_size  = int(len(X_train_full) * 0.1)
    X_val,   y_val   = X_train_full[:val_size],  y_train_full[:val_size]
    X_train, y_train = X_train_full[val_size:],  y_train_full[val_size:]

    print(f"Train : {X_train.shape}  |  Val : {X_val.shape}  |  Test : {X_test.shape}")
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


# ═══════════════════════════════════════════════════════════════════════════
# 2. BUILD THE CNN
# ═══════════════════════════════════════════════════════════════════════════

def build_model(input_shape=(28, 28, 1), num_classes=10):
    """
    Architecture
    ────────────
    Block 1 – 32 filters, 3×3, BN, ReLU, MaxPool
    Block 2 – 64 filters, 3×3, BN, ReLU, MaxPool
    Block 3 – 128 filters, 3×3, BN, ReLU
    Head    – GlobalAvgPool → Dense(256) → Dropout → Softmax
    """
    model = keras.Sequential([
        # ── Block 1 ──────────────────────────────────────────────────────
        layers.Conv2D(32, (3, 3), padding="same", input_shape=input_shape),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Conv2D(32, (3, 3), padding="same"),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        # ── Block 2 ──────────────────────────────────────────────────────
        layers.Conv2D(64, (3, 3), padding="same"),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Conv2D(64, (3, 3), padding="same"),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        # ── Block 3 ──────────────────────────────────────────────────────
        layers.Conv2D(128, (3, 3), padding="same"),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(0.25),

        # ── Classification Head ───────────────────────────────────────────
        layers.GlobalAveragePooling2D(),
        layers.Dense(256, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation="softmax"),
    ], name="DigitCNN")

    return model


# ═══════════════════════════════════════════════════════════════════════════
# 3. DATA AUGMENTATION
# ═══════════════════════════════════════════════════════════════════════════

def make_augmentation_layer():
    """Light augmentation that mirrors real handwriting variance."""
    return keras.Sequential([
        layers.RandomRotation(0.08),          # ±29°
        layers.RandomZoom(0.1),               # ±10 %
        layers.RandomTranslation(0.1, 0.1),   # shift up to 10 % each axis
    ], name="augmentation")


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRAIN
# ═══════════════════════════════════════════════════════════════════════════

def train(model, X_train, y_train, X_val, y_val, epochs=30, batch_size=128):
    augment = make_augmentation_layer()

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    callbacks = [
        EarlyStopping(monitor="val_accuracy", patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6, verbose=1),
        ModelCheckpoint("best_model.keras", monitor="val_accuracy", save_best_only=True, verbose=0),
    ]

    # Build a tf.data pipeline with augmentation on the fly
    AUTOTUNE = tf.data.AUTOTUNE

    train_ds = (
        tf.data.Dataset.from_tensor_slices((X_train, y_train))
        .shuffle(10_000)
        .batch(batch_size)
        .map(lambda x, y: (augment(x, training=True), y), num_parallel_calls=AUTOTUNE)
        .prefetch(AUTOTUNE)
    )

    val_ds = (
        tf.data.Dataset.from_tensor_slices((X_val, y_val))
        .batch(batch_size)
        .prefetch(AUTOTUNE)
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1,
    )
    return history


# ═══════════════════════════════════════════════════════════════════════════
# 5. EVALUATE & VISUALISE
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_and_plot(model, X_test, y_test, history):
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n{'─'*40}")
    print(f"  Test Accuracy : {test_acc*100:.2f} %")
    print(f"  Test Loss     : {test_loss:.4f}")
    print(f"{'─'*40}\n")

    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    print(classification_report(y_test, y_pred, target_names=[str(i) for i in range(10)]))

    os.makedirs("plots", exist_ok=True)

    # ── Training curves ───────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history.history["accuracy"],     label="Train")
    axes[0].plot(history.history["val_accuracy"], label="Val")
    axes[0].set_title("Accuracy"); axes[0].legend()

    axes[1].plot(history.history["loss"],     label="Train")
    axes[1].plot(history.history["val_loss"], label="Val")
    axes[1].set_title("Loss"); axes[1].legend()

    plt.tight_layout()
    plt.savefig("plots/training_curves.png", dpi=120)
    plt.close()
    print("Saved → plots/training_curves.png")

    # ── Confusion matrix ──────────────────────────────────────────────────
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=range(10), yticklabels=range(10))
    plt.xlabel("Predicted"); plt.ylabel("Actual")
    plt.title("Confusion Matrix — Test Set")
    plt.tight_layout()
    plt.savefig("plots/confusion_matrix.png", dpi=120)
    plt.close()
    print("Saved → plots/confusion_matrix.png")

    # ── Sample predictions ────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 10, figsize=(20, 4))
    for i in range(10):
        idx = np.where(y_test == i)[0][0]
        axes[0, i].imshow(X_test[idx].squeeze(), cmap="gray")
        axes[0, i].axis("off")
        axes[0, i].set_title(f"True:{y_test[idx]}", fontsize=8)

        axes[1, i].imshow(X_test[idx].squeeze(), cmap="gray")
        axes[1, i].axis("off")
        color = "green" if y_pred[idx] == y_test[idx] else "red"
        axes[1, i].set_title(f"Pred:{y_pred[idx]}", fontsize=8, color=color)

    plt.suptitle("Sample Predictions (row 1 = ground truth, row 2 = predicted)")
    plt.tight_layout()
    plt.savefig("plots/sample_predictions.png", dpi=120)
    plt.close()
    print("Saved → plots/sample_predictions.png")


# ═══════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("── Loading MNIST data ──────────────────────────────────────────")
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()

    print("\n── Building CNN ────────────────────────────────────────────────")
    model = build_model()
    model.summary()

    print("\n── Training ────────────────────────────────────────────────────")
    history = train(model, X_train, y_train, X_val, y_val, epochs=30)

    print("\n── Evaluating ──────────────────────────────────────────────────")
    evaluate_and_plot(model, X_test, y_test, history)

    model.save("digit_recognizer.keras")
    print("\nModel saved → digit_recognizer.keras")
    print("Run  `python app.py`  to launch the interactive drawing app.")
