class FaceError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


MESSAGES = {
    'no_face': '没有检测到人脸，请正对光源再拍',
    'multiple_faces': '画面中有多张人脸，请单独拍摄',
    'image_invalid': '图片无法解析',
    'image_too_large': '图片不能超过 2MB',
    'not_enrolled': '请先完成人脸采集',
    'below_threshold': '人脸比对未通过',
    'engine_unavailable': '人脸识别引擎未就绪',
}


def face_message(code):
    return MESSAGES.get(code, '人脸处理失败')
