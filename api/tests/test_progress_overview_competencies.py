import uuid
from types import SimpleNamespace

import pytest

from app.modules.assistant_tools.schemas import CompetencyDistribution, CompetencyProgress, EnrollmentProgress, LevelCount
from app.modules.learning import overview_service as service


@pytest.mark.parametrize('suppressed,has_data', [(False, True), (False, False), (True, True), (True, False)])
def test_competency_section_uses_current_framework_without_individual_levels(monkeypatch, suppressed, has_data):
    individual = uuid.uuid4()
    entry = CompetencyDistribution(codigo='C1', nombre='Synthetic competency', counts=LevelCount(level_1=1, level_2=2, level_3=0, not_assessed=2))
    source = CompetencyProgress(framework_version=3, suppressed=suppressed, min_group_size=5, distribution=[entry],
        items=[EnrollmentProgress(enrollment_id=individual, levels={'C1': 2})])
    calls = []

    def query(db, cohort_id, per_person):
        calls.append((cohort_id, per_person))
        return source, has_data

    monkeypatch.setattr(service, 'competency_progress', query)
    result = service.competencies_section(object(), SimpleNamespace(id='COH-SYN'))
    assert calls == [('COH-SYN', False)]
    assert result.framework_version == 3 and result.period == 'current_assigned_framework'
    assert result.has_data is (None if suppressed else has_data)
    assert 'enrollment_id' not in result.model_dump_json() and str(individual) not in result.model_dump_json()
    assert result.distribution[0].counts == (None if suppressed else entry.counts)


def test_missing_framework_does_not_become_version_zero_or_a_level_zero(monkeypatch):
    empty = CompetencyProgress(framework_version=None, suppressed=False, min_group_size=5, distribution=[], items=[])
    monkeypatch.setattr(service, 'competency_progress', lambda *args, **kwargs: (empty, False))
    result = service.competencies_section(object(), SimpleNamespace(id='COH-SYN'))
    assert result.framework_version is None and result.has_data is False and result.distribution == []
