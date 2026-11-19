# Synthetic dropout experiments / Experimentos sintéticos de abandono

## KAN-179 / KAN-198 — evaluation / evaluación

ES: después de entrenar, ejecutar `python -m ml.dropout.evaluate --artifacts ml/artifacts/demo`. Produce `evaluation.json` y `evaluation.csv` con soporte, prevalencia, matriz de confusión, precisión/recall/F1, PR-AUC, Brier y bins de calibración. Cero soporte o métricas indefinidas se registran como null. La regla 3/6 informa cobertura y se abstiene con medias jornadas; su resultado binario no se presenta como probabilidad calibrada. Comparar soportes/cobertura antes de comparar filas. Los agregados describen snapshots correlacionados dentro de persona, no observaciones independientes ni intervalos de confianza.

EN: the same command writes a reproducible ML-only evaluation table for validation/test. Training data never fit preprocessing on those periods. An experimental 25% review-capacity budget chooses the logistic threshold by F1 on validation only (highest-threshold tie break), never test labels. The shared threshold is also reported for Dummy; its alert fraction may exceed the proposed budget. One-class validation leaves threshold unset and any .5 diagnostic classification is labelled fallback, not a support policy. A threshold above 1 means no selected alerts. Hash checks bind dataset/model/evaluation. No synthetic metric establishes real calibration, fairness or intervention readiness; target/window/capacity and threshold still need Abdur/Elizabeth acceptance. This is the ML portion of KAN-198, not RAG/70% evaluation.

## ES

Responsable de tareas: Abdur. Cambios preparados con asistencia de Codex por Yohanna, sin reasignar Jira ni atribuir autoría a Abdur. Revisión técnica: David; definición de objetivo, esquema y aceptación: Elizabeth con Abdur. Solo prevención de abandono; nada de RAG ni decisiones sobre personas.

KAN-138 implementa un experimento **offline y sintético**, basado en la propuesta KAN-114, no una definición de abandono aprobada. La etiqueta es baja voluntaria confirmada en 14 días, no ausencia ni silencio. Casos sin seguimiento suficiente se censuran; casos ya retirados al corte no entrenan. La generación incluye una causa latente sintética compartida, ruido independiente para el resultado y la actividad, y eventos repetidos por persona. Esto facilita patrones artificiales: cualquier métrica puede estar inflada y no acredita validez real ni equidad.

Los datos académicos son un contrato de fixtures separado: no existen adaptadores a EDU-02/04, historia de rúbricas ni seed unificado del producto. KAN-173 queda pendiente. No se añaden columnas ni requisitos reales a PostgreSQL. Las competencias producen agregados, no columnas fijas por código. La señal ilustrativa 3/6 cuenta sesiones registradas, excluye pendientes y se abstiene si hay medias jornadas en la ventana, cuya equivalencia sigue pendiente.

Features: ventana de 14 días con eventos ocurridos y conocidos al corte; denominador cero produce null. Imputación/escalado se ajustan solo con entrenamiento. Personas y cohortes no cruzan particiones, y los horizontes de entrenamiento terminan antes del siguiente periodo. IDs, etiqueta, notas y estado final nunca entran al estimador. El baseline compara DummyClassifier y LogisticRegression; el artefacto JSON conserva parámetros numéricos, hashes, semilla y versiones, sin pickle ejecutable.

Dependencias aisladas en `ml/requirements.txt`: numpy/scipy/scikit-learn para el baseline solicitado y joblib/threadpoolctl como dependencias transitivas fijadas. No se añaden a la API ni se cambian sus imágenes. CI `dropout` verifica el experimento; pasar CI no valida el modelo ni cierra Jira. No subir artefactos entrenados, registros ni secretos al repo.

```powershell
python -m venv .venv-ml
.venv-ml/Scripts/python -m pip install -r ml/requirements.txt
.venv-ml/Scripts/python -m unittest discover -s ml/dropout/tests -v
.venv-ml/Scripts/python -m ml.dropout.train --out ml/artifacts/demo --seed 42 --people 300
```

En Linux: usar `.venv-ml/bin/python`. La ruta de salida es local e ignorada. Modelo no publicado, ni servidor ni datos reales. Las fechas, ventanas, umbrales y política de datos insuficientes de KAN-114 siguen pendientes de aceptación antes de cualquier uso funcional.

## EN

Task owner remains Abdur; changes prepared by Yohanna with Codex assistance, without Jira reassignment or impersonating authorship. David reviews methodology; Abdur/Elizabeth own target/schema acceptance. This is offline synthetic-only dropout work, never RAG or automated decisions about people.

The proposed 14-day confirmed-voluntary-withdrawal target is not an accepted client definition. Incomplete follow-up is censored; already withdrawn cases are outside the active population. Independent outcome noise and a shared synthetic latent cause are used, not a feature threshold masquerading as a label. Artificial correlations can inflate every metric: neither real-world validity nor fairness is established.

Academic fixtures are separate from the product schema: no EDU-02/04 adapter, historical rubric lifecycle or unified seed is delivered; KAN-173 remains pending. Competencies are aggregated dynamically. The illustrative 3/6 rule counts registered sessions and excludes unknowns; half-day parity remains unresolved, so that signal abstains when half-days occur in its window.

Only as-of observations enter 14-day features; zero exposure is null. Training-only preprocessing, person/cohort-disjoint temporal splits and horizon gaps guard leakage. Metadata/IDs, labels, notes and final state are excluded from estimator features. Dummy and logistic baselines use isolated pinned scientific dependencies, not API dependencies. JSON stores numeric parameters, seed, hashes and versions without executable pickle. See [SimpleImputer](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html) and [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).

Commands above use Windows paths; use `.venv-ml/bin/python` on Linux. Local generated artifacts stay ignored. CI verifies a demonstration pipeline only. No deployment, real data, task-completion claim or target/threshold acceptance. KAN-114 decisions remain pending before functional use.
