import os
import sys

import numpy as np
import torch
import torch.nn.functional as F

from capture_validation import DATASET_DIR
from app import CLASSES, MAX_FRAMES, device, model, _prepare_input

CONFIDENCE_THRESHOLD = 70.0
LEAKY_DIR = os.path.normcase(os.path.abspath(os.path.join(DATASET_DIR, "custom")))


def _load_samples(data_dir: str) -> list[tuple[str, str]]:
    samples = []
    for label in sorted(os.listdir(data_dir)):
        label_dir = os.path.join(data_dir, label)
        if not os.path.isdir(label_dir):
            continue
        for fname in sorted(os.listdir(label_dir)):
            if fname.endswith(".npy"):
                samples.append((os.path.join(label_dir, fname), label))
    return samples


def evaluate(data_dir: str) -> None:
    if model is None:
        print("No hay modelo entrenado (models/lstm*.pth no encontrado).")
        return

    if os.path.normcase(os.path.abspath(data_dir)) == LEAKY_DIR:
        print(
            f"ADVERTENCIA: evaluando sobre {data_dir}, el mismo dataset usado "
            "para entrenar. La accuracy resultante no mide generalización real."
        )

    if not os.path.isdir(data_dir):
        print(f"Directorio no encontrado: {data_dir}")
        return

    samples = _load_samples(data_dir)
    if not samples:
        print(f"No se encontraron muestras .npy en {data_dir}")
        return

    class_to_idx = {c: i for i, c in enumerate(CLASSES)}
    unknown_labels = sorted({label for _, label in samples if label not in class_to_idx})
    if unknown_labels:
        print(f"Etiquetas desconocidas para el modelo (se ignoran): {unknown_labels}")
        samples = [(p, l) for p, l in samples if l in class_to_idx]

    n = len(CLASSES)
    confusion = [[0] * n for _ in range(n)]
    below_threshold = 0
    correct = 0

    for path, true_label in samples:
        data = np.load(path).astype(np.float32)
        data = _prepare_input(data)
        input_tensor = torch.tensor(data, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = F.softmax(outputs, dim=1)
            confidence, predicted_idx = torch.max(probs, 1)

        pred_idx = predicted_idx.item()
        true_idx = class_to_idx[true_label]
        confusion[true_idx][pred_idx] += 1
        if pred_idx == true_idx:
            correct += 1
        if confidence.item() * 100 < CONFIDENCE_THRESHOLD:
            below_threshold += 1

    total = len(samples)
    accuracy = correct / total * 100

    print(f"Muestras evaluadas: {total} (MAX_FRAMES={MAX_FRAMES})")
    print(f"Accuracy global: {accuracy:.2f}%")
    print(
        f"Muestras bajo umbral de confianza ({CONFIDENCE_THRESHOLD:.0f}%): "
        f"{below_threshold}/{total}"
    )
    print()
    print(f"{'Clase':<12}{'Precision':>12}{'Recall':>12}{'Support':>10}")
    for i, cls in enumerate(CLASSES):
        support = sum(confusion[i])
        tp = confusion[i][i]
        predicted_count = sum(confusion[r][i] for r in range(n))
        precision = (tp / predicted_count * 100) if predicted_count else 0.0
        recall = (tp / support * 100) if support else 0.0
        print(f"{cls:<12}{precision:>11.2f}%{recall:>11.2f}%{support:>10d}")

    print()
    print("Matriz de confusión (filas=real, columnas=predicho):")
    header = "".ljust(12) + "".join(c[:10].ljust(10) for c in CLASSES)
    print(header)
    for i, cls in enumerate(CLASSES):
        row = cls.ljust(12) + "".join(str(confusion[i][j]).ljust(10) for j in range(n))
        print(row)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python eval_model.py <directorio_dataset>")
        sys.exit(1)
    evaluate(sys.argv[1])
