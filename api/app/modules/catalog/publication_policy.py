from app.core.authz import Scope
from app.core.errors import UserFacingError


def require_publication_admin(actor):
    # No additional roles or scope grants until product ownership confirms them.
    actor.require('catalog.publish', Scope())


def require_published(call):
    if call is None or call.publication_state != 'published':
        raise UserFacingError(404, 'public_course_not_found', 'No encontramos esta oferta publicada. Consulta el catálogo actualizado.')


def check_publication_version(call, expected_version):
    if call.publication_version != expected_version:
        raise UserFacingError(409, 'publication_version_conflict', 'La publicación ha cambiado. Actualiza la información antes de volver a intentarlo.')
