import threading
from io import BytesIO

from django.conf import settings

from apps.facecore.errors import FaceError

_model = None
_lock = threading.Lock()


def extract_embedding(image_bytes):
    if not image_bytes:
        raise FaceError('image_invalid')
    if len(image_bytes) > 2 * 1024 * 1024:
        raise FaceError('image_too_large')
    try:
        from PIL import Image
        import numpy as np
    except Exception as exc:
        raise FaceError('engine_unavailable') from exc
    try:
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
    except Exception as exc:
        raise FaceError('image_invalid') from exc
    image.thumbnail((1280, 1280))
    array = np.array(image)[:, :, ::-1]
    model = _load_model()
    with _lock:
        try:
            faces = model.get(array)
        except FaceError:
            raise
        except Exception as exc:
            raise FaceError('image_invalid') from exc
    if not faces:
        raise FaceError('no_face')
    if len(faces) > 1:
        raise FaceError('multiple_faces')
    embedding = np.array(faces[0].normed_embedding, dtype=np.float32)
    norm = float(np.linalg.norm(embedding))
    if norm == 0:
        raise FaceError('no_face')
    embedding = embedding / norm
    return [float(value) for value in embedding.tolist()]


def compare(live, enrolled):
    try:
        import numpy as np
    except Exception as exc:
        raise FaceError('engine_unavailable') from exc
    left = np.array(live, dtype=np.float32)
    right = np.array(enrolled, dtype=np.float32)
    if left.shape != right.shape or left.size != 512:
        raise FaceError('image_invalid')
    return float(np.dot(left, right))


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from insightface.app import FaceAnalysis
    except Exception as exc:
        raise FaceError('engine_unavailable') from exc
    root = settings.FACE_MODEL_ROOT
    root.mkdir(parents=True, exist_ok=True)
    try:
        application = FaceAnalysis(
            name='buffalo_s',
            root=str(root),
            providers=['CPUExecutionProvider'],
        )
        application.prepare(ctx_id=-1, det_size=(640, 640))
    except Exception as exc:
        raise FaceError('engine_unavailable') from exc
    _model = application
    return _model
