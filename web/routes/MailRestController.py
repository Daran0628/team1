from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from core.response.ApiResponse import ApiResponse
from core.response.ErrorStatus import ErrorStatus
from core.response.SuccessStatus import SuccessStatus
from service.MailService.MailService import MailService

mail_bp = Blueprint("mail", __name__, url_prefix="/api/mail")
_service = MailService()


@mail_bp.route("/mailbox", methods=["POST"])
@jwt_required()
def create_mailbox():
    data       = request.get_json()
    account_id = data.get("account_id")
    name_ko    = data.get("name_ko", account_id)
    ok = _service.create_mailbox(account_id, name_ko)
    if not ok:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR)
    return ApiResponse.on_success(SuccessStatus.MAIL_MAILBOX_CREATE)


@mail_bp.route("/inbox", methods=["GET"])
@jwt_required()
def get_inbox():
    account_id = get_jwt_identity()
    try:
        messages = _service.get_inbox(account_id)
        return ApiResponse.on_success(SuccessStatus.MAIL_INBOX_SUCCESS, messages)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/message/<uid>", methods=["GET"])
@jwt_required()
def get_message(uid):
    account_id = get_jwt_identity()
    try:
        message = _service.get_message(account_id, uid)
        return ApiResponse.on_success(SuccessStatus.MAIL_MESSAGE_SUCCESS, message)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/send", methods=["POST"])
@jwt_required()
def send_email():
    account_id = get_jwt_identity()
    data    = request.get_json()
    to      = data.get("to", "")
    subject = data.get("subject", "")
    body    = data.get("body", "")
    if not to or not subject:
        return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST)
    try:
        _service.send_email(account_id, to, subject, body)
        return ApiResponse.on_success(SuccessStatus.MAIL_SEND_SUCCESS)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/message/<uid>", methods=["DELETE"])
@jwt_required()
def delete_message(uid):
    account_id = get_jwt_identity()
    try:
        _service.delete_message(account_id, uid)
        return ApiResponse.on_success(SuccessStatus.MAIL_DELETE_SUCCESS)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/sent", methods=["GET"])
@jwt_required()
def get_sent():
    account_id = get_jwt_identity()
    try:
        messages = _service.get_sent(account_id)
        return ApiResponse.on_success(SuccessStatus.MAIL_SENT_SUCCESS, messages)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/sent/<uid>", methods=["GET"])
@jwt_required()
def get_sent_message(uid):
    account_id = get_jwt_identity()
    try:
        message = _service.get_sent_message(account_id, uid)
        return ApiResponse.on_success(SuccessStatus.MAIL_MESSAGE_SUCCESS, message)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


@mail_bp.route("/sent/<uid>", methods=["DELETE"])
@jwt_required()
def delete_sent_message(uid):
    account_id = get_jwt_identity()
    try:
        _service.delete_sent_message(account_id, uid)
        return ApiResponse.on_success(SuccessStatus.MAIL_DELETE_SUCCESS)
    except Exception as e:
        return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))
