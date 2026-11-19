"""Generate a bilingual model card from actual hash-bound experiment artifacts."""
import argparse
import json
from pathlib import Path

from ml.dropout.data import digest


def render_card(dataset, model, evaluation):
    if digest(dataset) != model["dataset_hash"] or digest(model) != evaluation["model_hash"] or digest(dataset) != evaluation["dataset_hash"]:
        raise ValueError("Card provenance mismatch")
    lines = ["# Model card / Ficha del modelo — SYNTHETIC ONLY", "",
             "**NOT VALIDATED FOR PEOPLE / NO VALIDADO PARA PERSONAS. No deployment or automatic decisions / sin despliegue ni decisiones automáticas.**", "",
             f"Protocol / protocolo: `{model['protocol']}`; seed / semilla: `{model['seed']}`.",
             f"Dataset SHA256: `{model['dataset_hash']}`; model SHA256: `{digest(model)}`.",
             f"Evaluation SHA256: `{digest(evaluation)}`.", f"Environment / entorno: `{json.dumps(model['versions'], sort_keys=True)}`.", "",
             "## EN — intended use and limits", "",
             "Offline engineering demonstration for Abdur's KAN-138/179/180/189/198 tasks. The proposed target is a human-confirmed voluntary withdrawal within 14 days of an active-enrollment cutoff; client/PO acceptance is pending. No real training, external validity, fairness certification or human intervention policy is established.",
             "Person/cohort-disjoint temporal splits with horizon gaps; train-only imputation/scaling and missing indicators. IDs, sensitive attributes, free notes, labels and final state are excluded from estimator features. Synthetic latent causes and sampling can inflate metrics. Snapshots within one person are correlated; these point metrics are not confidence intervals.",
             "Scoring abstains on unknown/inactive population, low exposure, excessive unknown attendance or missing threshold. The technical 3-day/.5-missing limits, 25% review-capacity proposal and target/window require Abdur/Elizabeth approval. Observed signals are not causal model attributions. No model chooses scope, changes enrollment, sanctions or excludes anyone.", "",
             "## ES — uso y límites", "",
             "Demostración técnica offline de las tareas ML de Abdur. Etiqueta propuesta: baja voluntaria confirmada por una persona en 14 días desde un corte de matrícula activa; aceptación pendiente. Datos totalmente sintéticos: no hay entrenamiento real, validez externa, certificación de equidad ni política de intervención aprobada.",
             "Personas/cohortes y periodos separados, con margen del horizonte; imputación/escalado solo con entrenamiento y señales de ausencia de datos. IDs, atributos sensibles, notas, etiquetas y estado final no entran al estimador. Causas latentes artificiales pueden inflar métricas; snapshots de una persona están correlacionados y las cifras no son intervalos de confianza.",
             "Abstención con población desconocida/inactiva, poca exposición, mucha asistencia desconocida o sin umbral. Los límites técnicos propuestos (3 días/.5 desconocido), capacidad del 25% y definición de etiqueta requieren aceptación de Abdur/Elizabeth. Las señales observadas no son explicaciones causales. Sin decidir ámbito, matrícula, sanción o exclusión.", "",
             f"Threshold / umbral: `{evaluation['threshold']}`; chosen on / elegido en: validation; PO accepted / aceptado: false.", "",
             "## Reproduced results / Resultados reproducidos", "",
             "| Model / modelo | Split | n | Positives / positivos | Coverage / cobertura | Precision | Recall | F1 | PR-AUC | Brier |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in evaluation["results"]:
        values = [row[key] for key in ("model", "split", "n", "positives", "coverage", "precision", "recall", "f1", "pr_auc", "brier")]
        lines.append("| " + " | ".join("undefined" if value is None else str(round(value, 6)) if isinstance(value, float) else str(value) for value in values) + " |")
    lines += ["", "The session rule has abstentions and different support; compare coverage before metrics. Calibration bins/missingness are in evaluation.json. / La regla por sesiones tiene abstenciones y soporte distinto; comparar cobertura. Bins de calibración y datos ausentes en evaluation.json.", "",
              "Task owner / responsable: Abdur. Technical review / revisión: David. Target, data and ethics / aceptación: Elizabeth with Abdur. Prepared with Codex assistance by Yohanna; no acceptance or Jira completion implied.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()
    root = Path(args.artifacts)
    inputs = [json.loads((root / name).read_text(encoding="utf-8")) for name in ("dataset.json", "model.json", "evaluation.json")]
    (root / "model-card.md").write_text(render_card(*inputs), encoding="utf-8")
    print("Model card generated from real synthetic experiment artifacts; acceptance pending")
