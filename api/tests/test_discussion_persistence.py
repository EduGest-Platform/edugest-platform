"""PostgreSQL scope/parent constraints for the future discussion service."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.admissions.models import Application
from app.modules.discussions.models import DiscussionComment, DiscussionThread
from app.modules.identity.models import User


def thread(db, **changes):
    values = dict(scope_type='program', program_id='P-IA', subject='Synthetic thread', created_by=db.scalar(select(User.id)))
    row = DiscussionThread(**{**values, **changes})
    db.add(row)
    db.flush()
    return row


def test_program_and_application_threads_share_one_comment_model(db):
    one = thread(db)
    two = thread(db, scope_type='application', program_id=None, application_id=db.scalar(select(Application.id)))
    root = DiscussionComment(thread_id=one.id, actor_user_id=one.created_by, body='Synthetic root')
    db.add(root)
    db.flush()
    db.add(DiscussionComment(thread_id=one.id, parent_id=root.id, actor_user_id=one.created_by, body='Synthetic reply'))
    db.commit()
    assert one.id != two.id


@pytest.mark.parametrize('changes', [{'program_id': None}, {'scope_type': 'public'}, {'application_id': 'also_present'}])
def test_incoherent_thread_scope_is_rejected(db, changes):
    if changes.get('application_id') == 'also_present':
        changes = {'application_id': db.scalar(select(Application.id))}
    with pytest.raises(IntegrityError):
        thread(db, **changes)
    db.rollback()


def test_reply_cannot_reference_a_parent_from_another_thread(db):
    one, two = thread(db), thread(db)
    parent = DiscussionComment(thread_id=one.id, actor_user_id=one.created_by, body='Synthetic root')
    db.add(parent)
    db.flush()
    db.add(DiscussionComment(thread_id=two.id, parent_id=parent.id, actor_user_id=two.created_by, body='Synthetic invalid reply'))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
